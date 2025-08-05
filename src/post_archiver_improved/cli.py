from scrapper import scrape_community_posts, save_posts
from pathlib import Path
import argparse

def main():
    parser = argparse.ArgumentParser(description='YouTube Community Posts Scraper')
    parser.add_argument('channel_id', help='YouTube channel ID')
    parser.add_argument('-n', '--num-posts', type=int, default=float('inf'),
                      help='Number of posts to scrape (default: all)')
    parser.add_argument('-c', '--comments', action='store_true',
                      help='Extract comments for each post')
    parser.add_argument('--max-comments', type=int, default=100,
                      help='Maximum number of comments to extract per post (default: 100)')
    parser.add_argument('-o', '--output', type=Path, default=Path.cwd(),
                      help='Output directory (default: current directory)')
    
    args = parser.parse_args()
    
    try:
        # Scrape posts
        posts = scrape_community_posts(
            args.channel_id, 
            args.num_posts,
            extract_comments=args.comments,
            max_comments_per_post=args.max_comments
        )
        
        # Save posts
        output_file = save_posts(posts, args.channel_id, args.output)
        
        print(f"\nSuccessfully scraped {len(posts)} posts")
        print(f"Results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
