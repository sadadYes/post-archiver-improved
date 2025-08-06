"""
Comment extraction functionality for YouTube community posts.

This module handles the complex logic for extracting comments and replies
from YouTube's API responses, including continuation handling.
"""

import re
import time
from typing import List, Optional, Dict, Any

from .models import Comment, Author
from .exceptions import APIError, ParseError
from .logging_config import get_logger

logger = get_logger(__name__)


class CommentProcessor:
    """
    Processes comments from YouTube API responses.
    
    This class extends the basic CommentExtractor with full comment processing
    capabilities including reply extraction and continuation handling.
    """
    
    def __init__(self, api_client, comment_extractor):
        """
        Initialize comment processor.
        
        Args:
            api_client: YouTube API client instance
            comment_extractor: Basic comment extractor instance
        """
        self.api = api_client
        self.extractor = comment_extractor
        logger.debug("Comment processor initialized")
    
    def extract_comments(
        self,
        channel_id: str,
        post_id: str,
        max_comments: int = 100,
        max_replies_per_comment: int = 200
    ) -> List[Comment]:
        """
        Extract comments for a post using post detail API.
        
        Args:
            channel_id: YouTube channel ID
            post_id: Post ID
            max_comments: Maximum number of comments to extract
            max_replies_per_comment: Maximum number of replies per comment
        
        Returns:
            List of Comment objects
        """
        comments = []
        
        try:
            logger.debug(f"Starting comment extraction for post {post_id}")
            
            # Get post detail data which contains initial comments
            response = self.api.get_post_detail_data(channel_id, post_id)
            continuation_token = self._find_comment_continuation_token(response)
            
            if not continuation_token:
                logger.info("No comments found for this post")
                return comments
            
            # Process comment batches with continuation
            while continuation_token and len(comments) < max_comments:
                try:
                    logger.debug(f"Fetching comment batch (comments so far: {len(comments)})")
                    comment_response = self.api.get_continuation_data(continuation_token)
                    
                    new_comments = self._extract_comments_from_continuation(
                        comment_response, max_replies_per_comment
                    )
                    
                    if not new_comments:
                        logger.debug("No more comments found")
                        break
                    
                    comments.extend(new_comments)
                    logger.debug(f"Extracted {len(new_comments)} comments in this batch")
                    
                    # Find next continuation token
                    continuation_token = self._find_continuation_token(comment_response)
                    
                    if len(comments) >= max_comments:
                        logger.debug(f"Reached maximum comment limit: {max_comments}")
                        break
                    
                    # Rate limiting
                    time.sleep(0.5)
                    
                except APIError as e:
                    logger.warning(f"API error during comment extraction: {e}")
                    break
                except Exception as e:
                    logger.warning(f"Error during comment extraction: {e}")
                    break
            
            # Limit to requested number
            comments = comments[:max_comments]
            logger.info(f"Successfully extracted {len(comments)} comments for post {post_id}")
            
            return comments
            
        except Exception as e:
            logger.error(f"Error extracting comments for post {post_id}: {e}")
            return []
    
    def _find_comment_continuation_token(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Find the continuation token for loading comments from post detail response.
        
        Args:
            response: Post detail API response
        
        Returns:
            Continuation token or None if not found
        """
        try:
            contents = response.get('contents', {})
            if 'twoColumnBrowseResultsRenderer' not in contents:
                return None
            
            tabs = contents['twoColumnBrowseResultsRenderer'].get('tabs', [])
            for tab in tabs:
                if 'tabRenderer' not in tab:
                    continue
                
                tab_content = tab['tabRenderer'].get('content', {})
                section_list = tab_content.get('sectionListRenderer', {})
                sections = section_list.get('contents', [])
                
                for section in sections:
                    if 'itemSectionRenderer' not in section:
                        continue
                    
                    section_renderer = section['itemSectionRenderer']
                    if section_renderer.get('sectionIdentifier') == 'comment-item-section':
                        for item in section_renderer.get('contents', []):
                            if 'continuationItemRenderer' in item:
                                continuation_endpoint = item['continuationItemRenderer']['continuationEndpoint']
                                token = continuation_endpoint['continuationCommand']['token']
                                logger.debug(f"Found comment continuation token: {token[:20]}...")
                                return token
            
            return None
            
        except Exception as e:
            logger.warning(f"Error finding comment continuation token: {e}")
            return None
    
    def _extract_comments_from_continuation(
        self,
        response: Dict[str, Any],
        max_replies_per_comment: int = 200
    ) -> List[Comment]:
        """
        Extract comments from a continuation response.
        
        Args:
            response: Continuation API response
            max_replies_per_comment: Maximum number of replies per comment
        
        Returns:
            List of Comment objects
        """
        comments = []
        
        try:
            # Extract entity payloads for new format comments
            entity_payloads = []
            if 'frameworkUpdates' in response:
                framework_updates = response['frameworkUpdates']
                if 'entityBatchUpdate' in framework_updates:
                    mutations = framework_updates['entityBatchUpdate'].get('mutations', [])
                    entity_payloads = [m for m in mutations if 'payload' in m]
            
            # Process response endpoints
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
            
        except Exception as e:
            logger.warning(f"Error extracting comments from continuation: {e}")
        
        return comments
    
    def _process_comment_item(
        self,
        item: Dict[str, Any],
        entity_payloads: List[Dict[str, Any]],
        max_replies_per_comment: int
    ) -> Optional[Comment]:
        """
        Process a single comment item from the response.
        
        Args:
            item: Comment item from API response
            entity_payloads: Entity payloads for new format comments
            max_replies_per_comment: Maximum number of replies per comment
        
        Returns:
            Comment object or None if processing fails
        """
        try:
            if 'commentThreadRenderer' in item:
                thread_renderer = item['commentThreadRenderer']
                
                # Check for new format (commentViewModel)
                if 'commentViewModel' in thread_renderer:
                    return self._process_new_format_comment(
                        thread_renderer, entity_payloads, max_replies_per_comment
                    )
                
                # Check for old format (comment.commentRenderer)
                elif 'comment' in thread_renderer and 'commentRenderer' in thread_renderer['comment']:
                    return self._process_old_format_comment(thread_renderer, max_replies_per_comment)
            
            elif 'commentRenderer' in item:
                return self.extractor.extract_comment_from_renderer(item['commentRenderer'])
            
            return None
            
        except Exception as e:
            logger.warning(f"Error processing comment item: {e}")
            return None
    
    def _process_new_format_comment(
        self,
        thread_renderer: Dict[str, Any],
        entity_payloads: List[Dict[str, Any]],
        max_replies_per_comment: int
    ) -> Optional[Comment]:
        """
        Process comment in new format (commentViewModel).
        
        Args:
            thread_renderer: Thread renderer data
            entity_payloads: Entity payloads for comment data
            max_replies_per_comment: Maximum number of replies per comment
        
        Returns:
            Comment object or None if processing fails
        """
        try:
            view_model = thread_renderer['commentViewModel']['commentViewModel']
            comment_key = view_model.get('commentKey', '')
            toolbar_key = view_model.get('toolbarStateKey', '')
            inline_replies_key = view_model.get('inlineRepliesKey', '')
            
            # Find matching entities
            matching_entities = []
            reply_entities = []
            
            for entity in entity_payloads:
                entity_key = entity.get('entityKey', '')
                if entity_key in [comment_key, toolbar_key]:
                    matching_entities.append(entity)
                elif (entity_key.startswith(inline_replies_key) and 
                      'commentEntityPayload' in entity.get('payload', {})):
                    reply_entities.append(entity)
            
            if not matching_entities:
                return None
            
            # Extract main comment
            comment = self.extractor.extract_comment_from_entity(matching_entities)
            if not comment:
                return None
            
            # Extract inline replies
            for reply_entity in reply_entities:
                reply = self.extractor.extract_comment_from_entity([reply_entity])
                if reply and len(comment.replies) < max_replies_per_comment:
                    comment.replies.append(reply)
            
            # Extract replies from thread renderer if available
            replies_data = thread_renderer.get('replies', {})
            if 'commentRepliesRenderer' in replies_data:
                self._extract_replies_from_renderer(
                    replies_data['commentRepliesRenderer'], comment, max_replies_per_comment
                )
            
            return comment
            
        except Exception as e:
            logger.warning(f"Error processing new format comment: {e}")
            return None
    
    def _process_old_format_comment(
        self,
        thread_renderer: Dict[str, Any],
        max_replies_per_comment: int
    ) -> Optional[Comment]:
        """
        Process comment in old format (comment.commentRenderer).
        
        Args:
            thread_renderer: Thread renderer data
            max_replies_per_comment: Maximum number of replies per comment
        
        Returns:
            Comment object or None if processing fails
        """
        try:
            comment = self.extractor.extract_comment_from_renderer(
                thread_renderer['comment']['commentRenderer']
            )
            
            if not comment:
                return None
            
            # Extract replies if available
            replies_data = thread_renderer.get('replies', {})
            if 'commentRepliesRenderer' in replies_data:
                self._extract_replies_from_renderer(
                    replies_data['commentRepliesRenderer'], comment, max_replies_per_comment
                )
            
            return comment
            
        except Exception as e:
            logger.warning(f"Error processing old format comment: {e}")
            return None
    
    def _extract_replies_from_renderer(
        self,
        replies_renderer: Dict[str, Any],
        parent_comment: Comment,
        max_replies: int = 200
    ) -> None:
        """
        Extract replies from commentRepliesRenderer and add them to parent comment.
        
        Args:
            replies_renderer: Replies renderer data
            parent_comment: Parent comment to add replies to
            max_replies: Maximum number of replies to extract
        """
        try:
            initial_reply_count = len(parent_comment.replies)
            
            # Extract immediate replies
            if 'contents' in replies_renderer:
                for reply_item in replies_renderer['contents']:
                    if 'commentRenderer' in reply_item:
                        reply = self.extractor.extract_comment_from_renderer(reply_item['commentRenderer'])
                        if reply and len(parent_comment.replies) < max_replies:
                            parent_comment.replies.append(reply)
            
            replies_extracted = len(parent_comment.replies) - initial_reply_count
            logger.debug(f"Extracted {replies_extracted} immediate replies")
            
            # Fetch additional replies if continuation token exists
            continuation_token = self._get_reply_continuation_token(replies_renderer)
            if continuation_token and len(parent_comment.replies) < max_replies:
                remaining_replies = max_replies - len(parent_comment.replies)
                additional_replies = self._fetch_replies_from_continuation(
                    continuation_token, remaining_replies
                )
                parent_comment.replies.extend(additional_replies[:remaining_replies])
                
                logger.debug(f"Extracted {len(additional_replies)} additional replies")
            
        except Exception as e:
            logger.warning(f"Error extracting replies: {e}")
    
    def _get_reply_continuation_token(self, replies_renderer: Dict[str, Any]) -> Optional[str]:
        """
        Get continuation token for fetching more replies.
        
        Args:
            replies_renderer: Replies renderer data
        
        Returns:
            Continuation token or None if not found
        """
        try:
            # Check in continuations array (most common location)
            if 'continuations' in replies_renderer:
                for continuation in replies_renderer['continuations']:
                    if 'nextContinuationData' in continuation:
                        token = continuation['nextContinuationData'].get('continuation', '')
                        if token:
                            return token
                    elif 'buttonRenderer' in continuation:
                        # Sometimes the continuation is in a "Show more replies" button
                        button = continuation['buttonRenderer']
                        if 'command' in button and 'continuationCommand' in button['command']:
                            token = button['command']['continuationCommand'].get('token', '')
                            if token:
                                return token
            
            # Check in contents for continuationItemRenderer
            if 'contents' in replies_renderer:
                for item in replies_renderer['contents']:
                    if 'continuationItemRenderer' in item:
                        continuation_endpoint = item['continuationItemRenderer'].get('continuationEndpoint', {})
                        if 'continuationCommand' in continuation_endpoint:
                            token = continuation_endpoint['continuationCommand'].get('token', '')
                            if token:
                                return token
            
            # Check in viewReplies button
            if 'viewReplies' in replies_renderer:
                view_replies = replies_renderer['viewReplies']
                if 'buttonRenderer' in view_replies:
                    button = view_replies['buttonRenderer']
                    if 'command' in button and 'continuationCommand' in button['command']:
                        token = button['command']['continuationCommand'].get('token', '')
                        if token:
                            return token
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting reply continuation token: {e}")
            return None
    
    def _fetch_replies_from_continuation(
        self,
        continuation_token: str,
        max_replies: int = 200
    ) -> List[Comment]:
        """
        Fetch replies using a continuation token.
        
        Args:
            continuation_token: Continuation token for next batch
            max_replies: Maximum number of replies to fetch
        
        Returns:
            List of Comment objects
        """
        replies = []
        current_token = continuation_token
        fetch_attempts = 0
        max_attempts = 10  # Prevent infinite loops
        
        try:
            while (current_token and 
                   len(replies) < max_replies and 
                   fetch_attempts < max_attempts):
                
                fetch_attempts += 1
                logger.debug(f"Fetching reply batch {fetch_attempts} (replies so far: {len(replies)})")
                
                try:
                    # Use the reply-specific endpoint for better results
                    response = self.api.get_reply_continuation_data(current_token)
                    batch_replies = self._extract_replies_from_response(response)
                    
                    if not batch_replies:
                        # If no replies found, try the regular continuation endpoint as fallback
                        response = self.api.get_continuation_data(current_token)
                        batch_replies = self._extract_replies_from_response(response)
                    
                    if not batch_replies:
                        logger.debug("No more replies found")
                        break
                    
                    replies.extend(batch_replies)
                    logger.debug(f"Fetched {len(batch_replies)} replies in batch {fetch_attempts}")
                    
                    # Look for next continuation token
                    current_token = self._find_reply_continuation_token_in_response(response)
                    
                    if not current_token:
                        logger.debug("No more continuation tokens found")
                        break
                    
                    # Rate limiting
                    time.sleep(0.3)
                    
                except APIError as e:
                    logger.warning(f"API error fetching replies: {e}")
                    break
                except Exception as e:
                    logger.warning(f"Error fetching reply batch: {e}")
                    break
            
        except Exception as e:
            logger.warning(f"Error in reply continuation fetch: {e}")
        
        return replies[:max_replies]
    
    def _extract_replies_from_response(self, response: Dict[str, Any]) -> List[Comment]:
        """
        Extract replies from a continuation response.
        
        Args:
            response: API response containing replies
        
        Returns:
            List of Comment objects
        """
        replies = []
        
        try:
            # Handle standard continuation response
            if 'onResponseReceivedEndpoints' in response:
                for endpoint in response['onResponseReceivedEndpoints']:
                    items = []
                    if 'reloadContinuationItemsCommand' in endpoint:
                        items = endpoint['reloadContinuationItemsCommand'].get('continuationItems', [])
                    elif 'appendContinuationItemsAction' in endpoint:
                        items = endpoint['appendContinuationItemsAction'].get('continuationItems', [])
                    
                    for item in items:
                        if 'commentRenderer' in item:
                            reply = self.extractor.extract_comment_from_renderer(item['commentRenderer'])
                            if reply:
                                replies.append(reply)
                        elif 'commentThreadRenderer' in item:
                            thread_renderer = item['commentThreadRenderer']
                            if 'comment' in thread_renderer and 'commentRenderer' in thread_renderer['comment']:
                                reply = self.extractor.extract_comment_from_renderer(
                                    thread_renderer['comment']['commentRenderer']
                                )
                                if reply:
                                    replies.append(reply)
            
            # Handle entity-based replies (new format)
            if 'frameworkUpdates' in response:
                framework_updates = response['frameworkUpdates']
                if 'entityBatchUpdate' in framework_updates:
                    mutations = framework_updates['entityBatchUpdate'].get('mutations', [])
                    entity_payloads = [
                        m for m in mutations 
                        if 'payload' in m and 'commentEntityPayload' in m.get('payload', {})
                    ]
                    
                    for entity in entity_payloads:
                        reply = self.extractor.extract_comment_from_entity([entity])
                        if reply:
                            replies.append(reply)
            
        except Exception as e:
            logger.warning(f"Error extracting replies from response: {e}")
        
        return replies
    
    def _find_reply_continuation_token_in_response(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Find the next continuation token specifically for replies in a response.
        
        Args:
            response: API response to search
        
        Returns:
            Continuation token or None if not found
        """
        try:
            # Check standard locations
            if 'onResponseReceivedEndpoints' in response:
                for endpoint in response['onResponseReceivedEndpoints']:
                    items = []
                    if 'reloadContinuationItemsCommand' in endpoint:
                        items = endpoint['reloadContinuationItemsCommand'].get('continuationItems', [])
                    elif 'appendContinuationItemsAction' in endpoint:
                        items = endpoint['appendContinuationItemsAction'].get('continuationItems', [])
                    
                    for item in items:
                        if 'continuationItemRenderer' in item:
                            continuation_renderer = item['continuationItemRenderer']
                            
                            # Check for direct continuation endpoint
                            continuation_endpoint = continuation_renderer.get('continuationEndpoint', {})
                            if 'continuationCommand' in continuation_endpoint:
                                token = continuation_endpoint['continuationCommand'].get('token', '')
                                if token:
                                    return token
                            
                            # Check for button-based continuation
                            if 'button' in continuation_renderer:
                                button = continuation_renderer['button']
                                if 'buttonRenderer' in button:
                                    button_renderer = button['buttonRenderer']
                                    command = button_renderer.get('command', {})
                                    if 'continuationCommand' in command:
                                        token = command['continuationCommand'].get('token', '')
                                        if token:
                                            return token
            
            # Check in continuation data
            if 'continuationContents' in response:
                continuation_contents = response['continuationContents']
                if 'commentRepliesContinuation' in continuation_contents:
                    replies_continuation = continuation_contents['commentRepliesContinuation']
                    if 'continuations' in replies_continuation:
                        for continuation in replies_continuation['continuations']:
                            if 'nextContinuationData' in continuation:
                                return continuation['nextContinuationData'].get('continuation', '')
            
            return None
            
        except Exception as e:
            logger.warning(f"Error finding reply continuation token: {e}")
            return None
    
    def _find_continuation_token(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Find the next continuation token in a response.
        
        Args:
            response: API response to search
        
        Returns:
            Continuation token or None if not found
        """
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
            
            return None
            
        except Exception as e:
            logger.warning(f"Error finding continuation token: {e}")
            return None
