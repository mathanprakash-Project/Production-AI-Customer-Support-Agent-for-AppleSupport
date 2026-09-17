import os
import re
import json
import random
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from tqdm import tqdm
from pathlib import Path

logger = logging.getLogger(__name__)

def load_raw_data(csv_path: str) -> pd.DataFrame:
    """
    Load the CSV data handling specific data types.
    """
    logger.info(f"Loading raw data from {csv_path}...")
    dtype_dict = {
        'tweet_id': str,
        'author_id': str,
        'inbound': bool,
        'created_at': str,
        'text': str,
        'response_tweet_id': str,
        'in_response_to_tweet_id': str
    }
    df = pd.read_csv(csv_path, dtype=dtype_dict)
    logger.info(f"Loaded {len(df)} rows.")
    return df

def filter_brand(df: pd.DataFrame, brand: str) -> pd.DataFrame:
    """
    Filter the dataframe to tweets involving the target brand.
    """
    logger.info(f"Filtering dataset for brand: {brand}...")
    
    # outbound
    outbound_mask = df['author_id'] == brand
    brand_outbound = df[outbound_mask]
    
    # inbound that received a response from brand
    responded_to_ids = brand_outbound['in_response_to_tweet_id'].dropna().unique()
    inbound_mask = df['tweet_id'].isin(responded_to_ids)
    brand_inbound = df[inbound_mask]
    
    # replies to brand
    replies_to_brand = df[df['in_response_to_tweet_id'].isin(brand_outbound['tweet_id'])]
    
    combined = pd.concat([brand_outbound, brand_inbound, replies_to_brand]).drop_duplicates(subset=['tweet_id'])
    
    logger.info(f"Filtered down to {len(combined)} related tweets.")
    return combined

def reconstruct_threads(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Reconstruct conversation threads from the filtered dataframe.
    """
    logger.info("Reconstructing threads...")
    
    tweets = df.to_dict('records')
    tweet_map = {t['tweet_id']: t for t in tweets}
    
    threads = []
    
    parent_to_children = {}
    for t_id, t in tweet_map.items():
        parent_id = t.get('in_response_to_tweet_id')
        if pd.notna(parent_id) and parent_id in tweet_map:
            if parent_id not in parent_to_children:
                parent_to_children[parent_id] = []
            parent_to_children[parent_id].append(t_id)
            
    def dfs(node_id, current_path):
        current_path.append(node_id)
        children = parent_to_children.get(node_id, [])
        if not children:
            if len(current_path) > 1:
                thread_msgs = []
                for cid in current_path:
                    ct = tweet_map[cid]
                    thread_msgs.append({
                        'tweet_id': ct['tweet_id'],
                        'author_id': ct['author_id'],
                        'is_inbound': ct['inbound'],
                        'text': ct['text'],
                        'created_at': ct['created_at']
                    })
                
                brand = next((m['author_id'] for m in thread_msgs if not m['is_inbound']), "Unknown")
                customer_msgs = [m for m in thread_msgs if m['is_inbound']]
                brand_msgs = [m for m in thread_msgs if not m['is_inbound']]
                
                threads.append({
                    'thread_id': current_path[0],
                    'messages': thread_msgs,
                    'brand': brand,
                    'first_customer_message': customer_msgs[0]['text'] if customer_msgs else "",
                    'brand_reply': brand_msgs[0]['text'] if brand_msgs else ""
                })
        else:
            for child in children:
                dfs(child, current_path.copy())

    roots = []
    for t_id in tweet_map:
        parent_id = tweet_map[t_id].get('in_response_to_tweet_id')
        if pd.isna(parent_id) or parent_id not in tweet_map:
            roots.append(t_id)
            
    for root in tqdm(roots, desc="Building threads"):
        dfs(root, [])
        
    logger.info(f"Reconstructed {len(threads)} threads.")
    return threads

def clean_text(text: str) -> str:
    """
    Clean tweet text by removing agent sign-offs, normalising whitespace, and handling URLs.
    """
    if not isinstance(text, str):
        return ""
        
    text = re.sub(r'\s*\^[A-Za-z0-9]+$', '', text)
    text = re.sub(r'https?://t\.co/\w+', '[URL]', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def subsample_threads(threads: List[Dict[str, Any]], n: int, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Randomly subsample threads ensuring diversity.
    """
    if len(threads) <= n:
        return threads
        
    random.seed(seed)
    
    lengths = {}
    for t in threads:
        l = len(t['messages'])
        if l not in lengths:
            lengths[l] = []
        lengths[l].append(t)
        
    return random.sample(threads, n)

def run_preprocessing(csv_path: str, brand: str, subsample_size: int, output_dir: str) -> str:
    """
    Orchestrate the preprocessing pipeline.
    """
    df = load_raw_data(csv_path)
    df = filter_brand(df, brand)
    
    logger.info("Cleaning text...")
    df['text'] = df['text'].apply(clean_text)
    
    threads = reconstruct_threads(df)
    
    if subsample_size > 0:
        logger.info(f"Subsampling to {subsample_size} threads...")
        threads = subsample_threads(threads, subsample_size)
        
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, 'threads.jsonl')
    
    logger.info(f"Saving {len(threads)} threads to {out_path}...")
    with open(out_path, 'w', encoding='utf-8') as f:
        for t in threads:
            f.write(json.dumps(t) + '\n')
            
    avg_len = sum(len(t['messages']) for t in threads) / len(threads) if threads else 0
    total_inbound = sum(sum(1 for m in t['messages'] if m['is_inbound']) for t in threads)
    total_outbound = sum(sum(1 for m in t['messages'] if not m['is_inbound']) for t in threads)
    in_out_ratio = total_inbound / total_outbound if total_outbound else 0
    
    logger.info(f"Summary Stats:")
    logger.info(f"Total threads: {len(threads)}")
    logger.info(f"Average thread length: {avg_len:.2f}")
    logger.info(f"Inbound/Outbound ratio: {in_out_ratio:.2f}")
    
    return out_path
