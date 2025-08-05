import json
import base64
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError


def make_http_request(url: str, data: Dict = None, headers: Dict = None, method: str = 'GET') -> Dict:
    """
    Utility function to make HTTP requests using urllib.
    
    Args:
        url: The URL to make the request to
        data: Dictionary to be sent as JSON payload (for POST requests)
        headers: Dictionary of headers to include in the request
        method: HTTP method ('GET' or 'POST')
    
    Returns:
        Dictionary containing the JSON response
    
    Raises:
        Exception: If the request fails
    """
    try:
        if data is not None:
            json_data = json.dumps(data).encode('utf-8')
        else:
            json_data = None
        
        request = Request(url, data=json_data, headers=headers or {}, method=method)
        
        with urlopen(request) as response:
            if response.status < 200 or response.status >= 300:
                raise Exception(f"HTTP {response.status}: {response.reason}")
            
            response_data = response.read().decode('utf-8')
            return json.loads(response_data)
            
    except HTTPError as e:
        raise Exception(f"HTTP error {e.code}: {e.reason}")
    except URLError as e:
        raise Exception(f"URL error: {e.reason}")
    except json.JSONDecodeError as e:
        raise Exception(f"JSON decode error: {e}")
    except Exception as e:
        raise Exception(f"Request failed: {str(e)}")


class YouTubeCommunityAPI:
    def __init__(self):
        self.base_url = "https://www.youtube.com/youtubei/v1/browse"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "X-YouTube-Client-Name": "1",
            "X-YouTube-Client-Version": "2.20241113.07.00",
            "Origin": "https://www.youtube.com",
            "Referer": "https://www.youtube.com/"
        }
        self.client_context = {
            "client": {
                "hl": "en-GB",
                "clientName": "WEB",
                "clientVersion": "2.20241113.07.00"
            },
            "user": {
                "lockedSafetyMode": False
            }
        }
    
    def _make_request(self, url: str, payload: Dict) -> Dict:
        """Make a POST request to YouTube API."""
        try:
            return make_http_request(url, data=payload, headers=self.headers, method='POST')
        except Exception as e:
            raise Exception(f"API request failed: {str(e)}")
    
    def get_initial_data(self, channel_id: str) -> Dict:
        """Get initial community tab data."""
        payload = {
            "context": self.client_context,
            "browseId": channel_id,
            "params": "Egljb21tdW5pdHnyBgQKAkoA"
        }
        return self._make_request(self.base_url, payload)
    
    def get_continuation_data(self, continuation_token: str) -> Dict:
        """Get next batch of posts using continuation token."""
        payload = {
            "context": self.client_context,
            "continuation": continuation_token
        }
        return self._make_request(self.base_url, payload)
    
    def get_post_detail_data(self, channel_id: str, post_id: str) -> Dict:
        """Get post detail data which includes comments."""
        channel_bytes = channel_id.encode()
        post_bytes = post_id.encode()
        
        params_data = (
            b'\xc2\x03Z\x12' + 
            bytes([len(channel_bytes)]) + channel_bytes +
            b'\x1a' + bytes([len(post_bytes)]) + post_bytes +
            b'Z' + bytes([len(channel_bytes)]) + channel_bytes
        )
        
        params = base64.b64encode(params_data).decode()
        
        payload = {
            "context": self.client_context,
            "browseId": "FEpost_detail",
            "params": params
        }
        return self._make_request(self.base_url, payload)

class PostExtractor:
    @staticmethod
    def extract_text_content(content_runs: List[Dict]) -> str:
        """Extract text content from runs format."""
        return ''.join(run.get('text', '') for run in content_runs)
    
    @staticmethod
    def _extract_author_info(post_renderer: Dict) -> Dict:
        """Extract author information from post renderer."""
        author_info = {
            'author': '',
            'author_id': '',
            'author_url': '',
            'author_thumbnail': '',
            'author_is_verified': False,
            'author_is_member': False
        }
        
        author_text = post_renderer.get('authorText', {})
        if 'runs' in author_text and author_text['runs']:
            author_info['author'] = author_text['runs'][0].get('text', '')
            author_endpoint = author_text['runs'][0].get('navigationEndpoint', {})
            if 'browseEndpoint' in author_endpoint:
                author_info['author_id'] = author_endpoint['browseEndpoint'].get('browseId', '')
                author_info['author_url'] = f"https://www.youtube.com{author_endpoint['browseEndpoint'].get('canonicalBaseUrl', '')}"
        
        author_thumbnail = post_renderer.get('authorThumbnail', {}).get('thumbnails', [])
        if author_thumbnail:
            author_info['author_thumbnail'] = author_thumbnail[-1].get('url', '')
        
        badges = post_renderer.get('authorBadges', [])
        for badge in badges:
            if 'metadataBadgeRenderer' in badge:
                badge_type = badge['metadataBadgeRenderer'].get('style', '')
                if 'BADGE_STYLE_TYPE_VERIFIED' in badge_type:
                    author_info['author_is_verified'] = True
                elif 'BADGE_STYLE_TYPE_MEMBER' in badge_type:
                    author_info['author_is_member'] = True
        
        return author_info
    
    @staticmethod
    def _extract_content_and_links(post_renderer: Dict) -> tuple:
        """Extract content text and links from post renderer."""
        content = ''
        links = []
        
        content_text = post_renderer.get('contentText', {})
        if 'runs' in content_text:
            content = PostExtractor.extract_text_content(content_text['runs'])
            for run in content_text['runs']:
                if 'navigationEndpoint' in run:
                    url = run.get('navigationEndpoint', {}).get('commandMetadata', {}).get(
                        'webCommandMetadata', {}).get('url', '')
                    if url:
                        if url.startswith('/'):
                            url = f'https://www.youtube.com{url}'
                        links.append({
                            'text': run.get('text', ''),
                            'url': url
                        })
        
        return content, links
    
    @staticmethod
    def _extract_images(attachment: Dict) -> List[Dict]:
        """Extract images from attachment data."""
        images = []
        
        if 'backstageImageRenderer' in attachment:
            thumbnails = attachment['backstageImageRenderer']['image']['thumbnails']
            if thumbnails:
                standard_url = thumbnails[0]['url']
                src_url = standard_url.split('=')[0] + '=s0'
                images.append({
                    'src': src_url
                })
        
        if 'postMultiImageRenderer' in attachment:
            for image in attachment['postMultiImageRenderer'].get('images', []):
                if 'backstageImageRenderer' in image:
                    thumbnails = image['backstageImageRenderer']['image']['thumbnails']
                    if thumbnails:
                        standard_url = thumbnails[0]['url']
                        src_url = standard_url.split('=')[0] + '=s0'
                        images.append({
                            'src': src_url
                        })
        
        return images
    
    @staticmethod
    def _is_timestamp_estimated(timestamp: str) -> bool:
        """Check if timestamp contains relative time indicators."""
        return any(
            word in timestamp.lower() 
            for word in ['hour', 'hours', 'minute', 'minutes', 'day', 'days', 
                        'week', 'weeks', 'month', 'months', 'year', 'years']
        )
    
    @staticmethod
    def extract_post_data(post_renderer: Dict) -> Dict:
        """Extract relevant data from a post renderer."""
        post_data = {
            'post_id': post_renderer.get('postId', ''),
            'content': '',
            'timestamp': '',
            'timestamp_estimated': False,
            'likes': '0',
            'comments_count': '0',
            'images': [],
            'links': [],
            'members_only': 'sponsorsOnlyBadge' in post_renderer
        }
        
        # Extract author information
        author_info = PostExtractor._extract_author_info(post_renderer)
        post_data.update(author_info)
        
        # Extract content and links
        content, links = PostExtractor._extract_content_and_links(post_renderer)
        post_data['content'] = content
        post_data['links'] = links
        
        # Extract timestamp
        timestamp = post_renderer.get('publishedTimeText', {}).get('runs', [{}])[0].get('text', '')
        post_data['timestamp'] = timestamp
        post_data['timestamp_estimated'] = PostExtractor._is_timestamp_estimated(timestamp)
        
        # Extract likes
        post_data['likes'] = post_renderer.get('voteCount', {}).get('simpleText', '0')
        
        # Extract comments count
        comment_count = post_renderer.get('actionButtons', {}).get('commentActionButtonsRenderer', {})\
            .get('replyButton', {}).get('buttonRenderer', {}).get('text', {}).get('simpleText', '0')
        post_data['comments_count'] = comment_count.split()[0] if comment_count else '0'
        
        # Extract images
        attachment = post_renderer.get('backstageAttachment', {})
        post_data['images'] = PostExtractor._extract_images(attachment)
        
        return post_data

class CommentExtractor:
    def __init__(self, api: YouTubeCommunityAPI):
        self.api = api
    
    @staticmethod
    def extract_text_content(content_runs: List[Dict]) -> str:
        """Extract text content from runs format."""
        return ''.join(run.get('text', '') for run in content_runs)
    
    def _create_comment_dict(self, comment_id: str, content: str, like_count: str, 
                           published_time: str, author_data: Dict) -> Dict:
        """Create a standardized comment dictionary."""
        return {
            'id': comment_id,
            'text': content,
            'like_count': like_count,
            'timestamp': published_time,
            'timestamp_estimated': True,
            'author_id': author_data.get('id', ''),
            'author': author_data.get('name', ''),
            'author_thumbnail': author_data.get('thumbnail', ''),
            'author_is_verified': author_data.get('is_verified', False),
            'author_is_member': author_data.get('is_member', False),
            'author_url': author_data.get('url', ''),
            'is_favorited': author_data.get('is_favorited', False),
            'is_pinned': author_data.get('is_pinned', False),
            'reply_count': author_data.get('reply_count', '0'),
            'replies': []
        }
    
    def extract_comment_from_entity(self, entity_payloads: List[Dict]) -> Optional[Dict]:
        """Extract comment from new entity format."""
        comment_entity = None
        toolbar_entity = None
        
        for entity in entity_payloads:
            payload = entity.get('payload', {})
            if 'commentEntityPayload' in payload:
                comment_entity = payload['commentEntityPayload']
            elif 'engagementToolbarStateEntityPayload' in payload:
                toolbar_entity = payload['engagementToolbarStateEntityPayload']
        
        if not comment_entity:
            return None
            
        properties = comment_entity.get('properties', {})
        comment_id = properties.get('commentId', '')
        if not comment_id:
            return None
        
        content = properties.get('content', {}).get('content', '')
        published_time = properties.get('publishedTime', '')
        
        author = comment_entity.get('author', {})
        author_url = self._extract_author_url(author)
        
        like_count, is_favorited, reply_count = self._extract_toolbar_data(
            comment_entity.get('toolbar', {}), toolbar_entity
        )
        
        author_data = {
            'id': author.get('channelId', ''),
            'name': author.get('displayName', ''),
            'thumbnail': author.get('avatarThumbnailUrl', ''),
            'is_verified': author.get('isVerified', False),
            'is_member': 'sponsorBadgeA11y' in author,
            'url': author_url,
            'is_favorited': is_favorited,
            'is_pinned': False,
            'reply_count': reply_count
        }
        
        return self._create_comment_dict(comment_id, content, like_count, published_time, author_data)
    
    def _extract_author_url(self, author: Dict) -> str:
        """Extract author URL from author data."""
        channel_command = author.get('channelCommand', {}).get('innertubeCommand', {})
        if 'browseEndpoint' in channel_command:
            canonical_url = channel_command['browseEndpoint'].get('canonicalBaseUrl', '')
            if canonical_url:
                return f"https://www.youtube.com{canonical_url}"
        elif 'commandMetadata' in channel_command:
            web_metadata = channel_command['commandMetadata'].get('webCommandMetadata', {})
            if 'url' in web_metadata:
                return f"https://www.youtube.com{web_metadata['url']}"
        return ''
    
    def _extract_toolbar_data(self, toolbar: Dict, toolbar_entity: Optional[Dict]) -> tuple:
        """Extract like count, favorited status, and reply count from toolbar data."""
        like_count = '0'
        is_favorited = False
        reply_count = '0'
        
        if toolbar:
            like_count = toolbar.get('likeCountA11y', toolbar.get('likeCountLiked', '0'))
            is_favorited = toolbar.get('heartState') == 'TOOLBAR_HEART_STATE_HEARTED'
            reply_count = toolbar.get('replyCountA11y', '0').split()[0] if toolbar.get('replyCountA11y') else '0'
        
        if toolbar_entity:
            toolbar_like_count = toolbar_entity.get('likeCountA11y', '0')
            if toolbar_like_count != '0':
                like_count = toolbar_like_count
            is_favorited = toolbar_entity.get('heartState') == 'TOOLBAR_HEART_STATE_HEARTED'
            toolbar_reply_count = toolbar_entity.get('replyCountA11y', '0').split()[0] if toolbar_entity.get('replyCountA11y') else '0'
            if toolbar_reply_count != '0':
                reply_count = toolbar_reply_count
        
        return like_count, is_favorited, reply_count
    
    def extract_comment_from_renderer(self, comment_renderer: Dict) -> Optional[Dict]:
        """Extract comment from old renderer format."""
        comment_id = comment_renderer.get('commentId', '')
        if not comment_id:
            return None
        
        content = self.extract_text_content(comment_renderer.get('contentText', {}).get('runs', []))
        like_count = comment_renderer.get('voteCount', {}).get('simpleText', '0')
        published_time = comment_renderer.get('publishedTimeText', {}).get('runs', [{}])[0].get('text', '')
        
        author_text = comment_renderer.get('authorText', {}).get('simpleText', '')
        author_endpoint = comment_renderer.get('authorEndpoint', {})
        author_id = author_endpoint.get('browseEndpoint', {}).get('browseId', '')
        canonical_url = author_endpoint.get('browseEndpoint', {}).get('canonicalBaseUrl', '')
        author_url = f"https://www.youtube.com{canonical_url}" if canonical_url else ''
        
        author_thumbnail = comment_renderer.get('authorThumbnail', {}).get('thumbnails', [{}])[-1].get('url', '')
        author_is_verified = any(
            badge.get('metadataBadgeRenderer', {}).get('style', '') == 'BADGE_STYLE_TYPE_VERIFIED'
            for badge in comment_renderer.get('authorBadges', [])
        )
        
        reply_count = comment_renderer.get('replyCount', '0')
        if isinstance(reply_count, dict):
            reply_count = reply_count.get('simpleText', '0')
        
        author_data = {
            'id': author_id,
            'name': author_text,
            'thumbnail': author_thumbnail,
            'is_verified': author_is_verified,
            'is_member': False,
            'url': author_url,
            'is_favorited': 'creatorHeart' in comment_renderer.get('actionButtons', {}),
            'is_pinned': 'pinnedCommentBadge' in comment_renderer,
            'reply_count': reply_count
        }
        
        return self._create_comment_dict(comment_id, content, like_count, published_time, author_data)
    
    def extract_comments(self, channel_id: str, post_id: str, max_comments: int = 100, 
                        max_replies_per_comment: int = 200) -> List[Dict]:
        """Extract comments for a post using post detail API."""
        comments = []
        
        try:
            response = self.api.get_post_detail_data(channel_id, post_id)
            continuation_token = self._find_comment_continuation_token(response)
            
            while continuation_token and len(comments) < max_comments:
                try:
                    comment_response = self.api.get_continuation_data(continuation_token)
                    new_comments = self._extract_comments_from_continuation(comment_response, max_replies_per_comment)
                    comments.extend(new_comments)
                    
                    continuation_token = self._find_continuation_token(comment_response)
                    
                    if len(comments) >= max_comments:
                        break
                        
                except Exception:
                    break
            
            return comments[:max_comments]
            
        except Exception:
            return []
    
    def _find_comment_continuation_token(self, response: Dict) -> Optional[str]:
        """Find the continuation token for loading comments."""
        try:
            contents = response.get('contents', {})
            if 'twoColumnBrowseResultsRenderer' in contents:
                tabs = contents['twoColumnBrowseResultsRenderer']['tabs']
                for tab in tabs:
                    if 'tabRenderer' in tab:
                        tab_content = tab['tabRenderer']['content']['sectionListRenderer']['contents']
                        for section in tab_content:
                            if 'itemSectionRenderer' in section:
                                section_renderer = section['itemSectionRenderer']
                                if section_renderer.get('sectionIdentifier') == 'comment-item-section':
                                    for item in section_renderer.get('contents', []):
                                        if 'continuationItemRenderer' in item:
                                            continuation_endpoint = item['continuationItemRenderer']['continuationEndpoint']
                                            return continuation_endpoint['continuationCommand']['token']
        except Exception:
            pass
        return None
    
    def _extract_comments_from_continuation(self, response: Dict, max_replies_per_comment: int = 200) -> List[Dict]:
        """Extract comments from a continuation response."""
        comments = []
        try:
            entity_payloads = []
            if 'frameworkUpdates' in response:
                framework_updates = response['frameworkUpdates']
                if 'entityBatchUpdate' in framework_updates:
                    mutations = framework_updates['entityBatchUpdate'].get('mutations', [])
                    entity_payloads = [m for m in mutations if 'payload' in m]
            
            if 'onResponseReceivedEndpoints' in response:
                for endpoint in response['onResponseReceivedEndpoints']:
                    items = []
                    if 'reloadContinuationItemsCommand' in endpoint:
                        items = endpoint['reloadContinuationItemsCommand'].get('continuationItems', [])
                    elif 'appendContinuationItemsAction' in endpoint:
                        items = endpoint['appendContinuationItemsAction'].get('continuationItems', [])
                    
                    for item in items:
                        comment = self._process_comment_item(item, entity_payloads, max_replies_per_comment)
                        if comment:
                            comments.append(comment)
                                
        except Exception:
            pass
        
        return comments
    
    def _process_comment_item(self, item: Dict, entity_payloads: List[Dict], max_replies_per_comment: int) -> Optional[Dict]:
        """Process a single comment item from the response."""
        if 'commentThreadRenderer' in item:
            thread_renderer = item['commentThreadRenderer']
            
            # Check for new format (commentViewModel)
            if 'commentViewModel' in thread_renderer:
                return self._process_new_format_comment(thread_renderer, entity_payloads, max_replies_per_comment)
            
            # Check for old format (comment.commentRenderer)
            elif 'comment' in thread_renderer and 'commentRenderer' in thread_renderer['comment']:
                return self._process_old_format_comment(thread_renderer, max_replies_per_comment)
        
        elif 'commentRenderer' in item:
            return self.extract_comment_from_renderer(item['commentRenderer'])
        
        return None
    
    def _process_new_format_comment(self, thread_renderer: Dict, entity_payloads: List[Dict], max_replies_per_comment: int) -> Optional[Dict]:
        """Process comment in new format (commentViewModel)."""
        view_model = thread_renderer['commentViewModel']['commentViewModel']
        comment_key = view_model.get('commentKey', '')
        toolbar_key = view_model.get('toolbarStateKey', '')
        inline_replies_key = view_model.get('inlineRepliesKey', '')
        
        matching_entities = []
        reply_entities = []
        
        for entity in entity_payloads:
            entity_key = entity.get('entityKey', '')
            if entity_key in [comment_key, toolbar_key]:
                matching_entities.append(entity)
            elif entity_key.startswith(inline_replies_key) and 'commentEntityPayload' in entity.get('payload', {}):
                reply_entities.append(entity)
        
        if matching_entities:
            comment = self.extract_comment_from_entity(matching_entities)
            if comment:
                # Extract replies if they exist
                for reply_entity in reply_entities:
                    reply = self.extract_comment_from_entity([reply_entity])
                    if reply:
                        comment['replies'].append(reply)
                
                # Also check if there are replies in the thread renderer
                replies_data = thread_renderer.get('replies', {})
                if 'commentRepliesRenderer' in replies_data:
                    self._extract_replies_from_renderer(replies_data['commentRepliesRenderer'], comment, max_replies_per_comment)
                
                return comment
        
        return None
    
    def _process_old_format_comment(self, thread_renderer: Dict, max_replies_per_comment: int) -> Optional[Dict]:
        """Process comment in old format (comment.commentRenderer)."""
        comment = self.extract_comment_from_renderer(thread_renderer['comment']['commentRenderer'])
        if comment:
            replies_data = thread_renderer.get('replies', {})
            if 'commentRepliesRenderer' in replies_data:
                self._extract_replies_from_renderer(replies_data['commentRepliesRenderer'], comment, max_replies_per_comment)
            return comment
        
        return None
    
    def _extract_replies_from_renderer(self, replies_renderer: Dict, parent_comment: Dict, max_replies: int = 200):
        """Extract replies from commentRepliesRenderer and add them to parent comment."""
        try:
            if 'contents' in replies_renderer:
                for reply_item in replies_renderer['contents']:
                    if 'commentRenderer' in reply_item:
                        reply = self.extract_comment_from_renderer(reply_item['commentRenderer'])
                        if reply and len(parent_comment['replies']) < max_replies:
                            parent_comment['replies'].append(reply)
            
            # Try to fetch additional replies if continuation token exists
            continuation_token = self._get_reply_continuation_token(replies_renderer)
            if continuation_token and len(parent_comment['replies']) < max_replies:
                additional_replies = self._fetch_replies_from_continuation(continuation_token, max_replies - len(parent_comment['replies']))
                parent_comment['replies'].extend(additional_replies[:max_replies - len(parent_comment['replies'])])
                
        except Exception as e:
            # Log error but don't break the entire process (hopefully)
            print(f"Error extracting replies for comment {parent_comment.get('id', 'unknown')}: {e}")
    
    def _get_reply_continuation_token(self, replies_renderer: Dict) -> Optional[str]:
        """Get continuation token for fetching more replies."""
        # Check in continuations array
        if 'continuations' in replies_renderer:
            for continuation in replies_renderer['continuations']:
                if 'nextContinuationData' in continuation:
                    return continuation['nextContinuationData'].get('continuation', '')
        
        # Also check in contents for continuationItemRenderer
        if 'contents' in replies_renderer:
            for item in replies_renderer['contents']:
                if 'continuationItemRenderer' in item:
                    continuation_endpoint = item['continuationItemRenderer'].get('continuationEndpoint', {})
                    if 'continuationCommand' in continuation_endpoint:
                        return continuation_endpoint['continuationCommand'].get('token', '')
        
        return None
    
    def _fetch_replies_from_continuation(self, continuation_token: str, max_replies: int = 200) -> List[Dict]:
        """Fetch replies using a continuation token."""
        replies = []
        current_token = continuation_token
        
        try:
            while current_token and len(replies) < max_replies:
                response = self.api.get_continuation_data(current_token)
                batch_replies = self._extract_replies_from_response(response)
                replies.extend(batch_replies)
                
                current_token = self._find_continuation_token(response)
                if not batch_replies or len(replies) >= max_replies:
                    break
                    
        except Exception as e:
            print(f"Error fetching replies from continuation: {e}")
        
        return replies[:max_replies]
    
    def _extract_replies_from_response(self, response: Dict) -> List[Dict]:
        """Extract replies from a continuation response."""
        replies = []
        
        if 'onResponseReceivedEndpoints' in response:
            for endpoint in response['onResponseReceivedEndpoints']:
                items = []
                if 'reloadContinuationItemsCommand' in endpoint:
                    items = endpoint['reloadContinuationItemsCommand'].get('continuationItems', [])
                elif 'appendContinuationItemsAction' in endpoint:
                    items = endpoint['appendContinuationItemsAction'].get('continuationItems', [])
                
                for item in items:
                    if 'commentRenderer' in item:
                        reply = self.extract_comment_from_renderer(item['commentRenderer'])
                        if reply:
                            replies.append(reply)
                    elif 'commentThreadRenderer' in item:
                        thread_renderer = item['commentThreadRenderer']
                        if 'comment' in thread_renderer and 'commentRenderer' in thread_renderer['comment']:
                            reply = self.extract_comment_from_renderer(thread_renderer['comment']['commentRenderer'])
                            if reply:
                                replies.append(reply)
        
        # Handle entity-based replies (new format)
        if 'frameworkUpdates' in response:
            framework_updates = response['frameworkUpdates']
            if 'entityBatchUpdate' in framework_updates:
                mutations = framework_updates['entityBatchUpdate'].get('mutations', [])
                entity_payloads = [m for m in mutations if 'payload' in m and 'commentEntityPayload' in m.get('payload', {})]
                
                for entity in entity_payloads:
                    reply = self.extract_comment_from_entity([entity])
                    if reply:
                        replies.append(reply)
        
        return replies
    
    def _find_continuation_token(self, response: Dict) -> Optional[str]:
        """Find the next continuation token in a response."""
        try:
            if 'onResponseReceivedEndpoints' in response:
                for endpoint in response['onResponseReceivedEndpoints']:
                    items = []
                    if 'reloadContinuationItemsCommand' in endpoint:
                        items = endpoint['reloadContinuationItemsCommand'].get('continuationItems', [])
                    elif 'appendContinuationItemsAction' in endpoint:
                        items = endpoint['appendContinuationItemsAction'].get('continuationItems', [])
                    
                    for item in items:
                        if 'continuationItemRenderer' in item:
                            continuation_endpoint = item['continuationItemRenderer']['continuationEndpoint']
                            return continuation_endpoint['continuationCommand']['token']
        except Exception:
            pass
        return None
    
def scrape_community_posts(
    channel_id: str, 
    max_posts: int = float('inf'), 
    extract_comments: bool = False,
    max_comments_per_post: int = 100
) -> List[Dict]:
    """Scrape community posts from a YouTube channel."""
    api = YouTubeCommunityAPI()
    comment_extractor = CommentExtractor(api) if extract_comments else None
    posts = []
    
    try:
        response = api.get_initial_data(channel_id)
        
        # Find the Community tab
        tabs = response['contents']['twoColumnBrowseResultsRenderer']['tabs']
        community_tab = None
        for tab in tabs:
            if 'tabRenderer' in tab and tab['tabRenderer'].get('title', '').lower() == 'posts':
                community_tab = tab['tabRenderer']
                break
        
        if not community_tab:
            raise Exception("Community tab not found")
        
        # Extract initial posts
        contents = community_tab['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents']
        
        # Get continuation token
        continuation_item = next(
            (item for item in contents if 'continuationItemRenderer' in item), None
        )
        token = (continuation_item['continuationItemRenderer']['continuationEndpoint']
                ['continuationCommand']['token'] if continuation_item else None)
        
        # Process initial posts
        posts.extend(_process_posts_batch(contents, channel_id, comment_extractor, 
                                        extract_comments, max_comments_per_post, max_posts))
        
        # Get remaining posts using continuation token
        while token and len(posts) < max_posts:
            response = api.get_continuation_data(token)
            contents = response['onResponseReceivedEndpoints'][0]['appendContinuationItemsAction']['continuationItems']
            
            # Get next continuation token
            continuation_item = next(
                (item for item in contents if 'continuationItemRenderer' in item), None
            )
            token = (continuation_item['continuationItemRenderer']['continuationEndpoint']
                    ['continuationCommand']['token'] if continuation_item else None)
            
            # Process posts
            new_posts = _process_posts_batch(contents, channel_id, comment_extractor, 
                                           extract_comments, max_comments_per_post, 
                                           max_posts - len(posts))
            posts.extend(new_posts)
    
    except Exception as e:
        raise Exception(f"Failed to parse YouTube response: {str(e)}")
    
    return posts

def _process_posts_batch(contents: List[Dict], channel_id: str, comment_extractor: Optional[CommentExtractor],
                        extract_comments: bool, max_comments_per_post: int, max_posts: int) -> List[Dict]:
    """Process a batch of posts from content list."""
    posts = []
    
    for content in contents:
        if 'backstagePostThreadRenderer' in content and len(posts) < max_posts:
            post_renderer = content['backstagePostThreadRenderer']['post']['backstagePostRenderer']
            post_data = PostExtractor.extract_post_data(post_renderer)
            
            # Extract comments if requested
            if extract_comments and comment_extractor and post_data['comments_count'] != '0':
                post_data['comments'] = comment_extractor.extract_comments(
                    channel_id, post_data['post_id'], max_comments_per_post
                )
            else:
                post_data['comments'] = []
            
            posts.append(post_data)
    
    return posts

def save_posts(posts: List[Dict], channel_id: str, output_dir: Optional[Path] = None) -> Path:
    """Save posts to a JSON file."""
    if not output_dir:
        output_dir = Path.cwd()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = output_dir / f'posts_{channel_id}_{timestamp}.json'
    
    data = {
        'channel_id': channel_id,
        'scrape_date': datetime.now().isoformat(),
        'scrape_timestamp': int(datetime.now().timestamp()),
        'posts_count': len(posts),
        'posts': posts
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filename

if __name__ == '__main__':
    posts = scrape_community_posts(
        channel_id="UC5CwaMl1eIgY8h02uZw7u8A",
        max_posts=1,
        extract_comments=True,
        max_comments_per_post=250
    )
    
    save_posts(posts, "UC5CwaMl1eIgY8h02uZw7u8A")
