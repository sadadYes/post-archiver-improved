"""
Data models for YouTube community posts and comments.

This module defines the data structures used to represent posts, comments,
and related metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class Author:
    """Represents a YouTube channel author."""
    id: str = ""
    name: str = ""
    url: str = ""
    thumbnail: str = ""
    is_verified: bool = False
    is_member: bool = False


@dataclass
class Link:
    """Represents a link within post or comment content."""
    text: str = ""
    url: str = ""


@dataclass
class Image:
    """Represents an image attachment."""
    src: str = ""
    local_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None


@dataclass
class Comment:
    """Represents a comment on a community post."""
    id: str = ""
    text: str = ""
    like_count: str = "0"
    timestamp: str = ""
    timestamp_estimated: bool = True
    author: Author = field(default_factory=Author)
    is_favorited: bool = False
    is_pinned: bool = False
    reply_count: str = "0"
    replies: List['Comment'] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert comment to dictionary format for JSON serialization."""
        return {
            'id': self.id,
            'text': self.text,
            'like_count': self.like_count,
            'timestamp': self.timestamp,
            'timestamp_estimated': self.timestamp_estimated,
            'author_id': self.author.id,
            'author': self.author.name,
            'author_thumbnail': self.author.thumbnail,
            'author_is_verified': self.author.is_verified,
            'author_is_member': self.author.is_member,
            'author_url': self.author.url,
            'is_favorited': self.is_favorited,
            'is_pinned': self.is_pinned,
            'reply_count': self.reply_count,
            'replies': [reply.to_dict() for reply in self.replies]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Comment':
        """Create Comment instance from dictionary."""
        author = Author(
            id=data.get('author_id', ''),
            name=data.get('author', ''),
            url=data.get('author_url', ''),
            thumbnail=data.get('author_thumbnail', ''),
            is_verified=data.get('author_is_verified', False),
            is_member=data.get('author_is_member', False)
        )
        
        replies = [cls.from_dict(reply_data) for reply_data in data.get('replies', [])]
        
        return cls(
            id=data.get('id', ''),
            text=data.get('text', ''),
            like_count=data.get('like_count', '0'),
            timestamp=data.get('timestamp', ''),
            timestamp_estimated=data.get('timestamp_estimated', True),
            author=author,
            is_favorited=data.get('is_favorited', False),
            is_pinned=data.get('is_pinned', False),
            reply_count=data.get('reply_count', '0'),
            replies=replies
        )


@dataclass
class Post:
    """Represents a YouTube community post."""
    post_id: str = ""
    content: str = ""
    timestamp: str = ""
    timestamp_estimated: bool = False
    likes: str = "0"
    comments_count: str = "0"
    members_only: bool = False
    author: Author = field(default_factory=Author)
    images: List[Image] = field(default_factory=list)
    links: List[Link] = field(default_factory=list)
    comments: List[Comment] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert post to dictionary format for JSON serialization."""
        return {
            'post_id': self.post_id,
            'content': self.content,
            'timestamp': self.timestamp,
            'timestamp_estimated': self.timestamp_estimated,
            'likes': self.likes,
            'comments_count': self.comments_count,
            'members_only': self.members_only,
            'author': self.author.name,
            'author_id': self.author.id,
            'author_url': self.author.url,
            'author_thumbnail': self.author.thumbnail,
            'author_is_verified': self.author.is_verified,
            'author_is_member': self.author.is_member,
            'images': [
                {
                    'src': img.src,
                    'local_path': img.local_path,
                    'width': img.width,
                    'height': img.height,
                    'file_size': img.file_size
                }
                for img in self.images
            ],
            'links': [{'text': link.text, 'url': link.url} for link in self.links],
            'comments': [comment.to_dict() for comment in self.comments]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        """Create Post instance from dictionary."""
        author = Author(
            id=data.get('author_id', ''),
            name=data.get('author', ''),
            url=data.get('author_url', ''),
            thumbnail=data.get('author_thumbnail', ''),
            is_verified=data.get('author_is_verified', False),
            is_member=data.get('author_is_member', False)
        )
        
        images = []
        for img_data in data.get('images', []):
            images.append(Image(
                src=img_data.get('src', ''),
                local_path=img_data.get('local_path'),
                width=img_data.get('width'),
                height=img_data.get('height'),
                file_size=img_data.get('file_size')
            ))
        
        links = []
        for link_data in data.get('links', []):
            links.append(Link(
                text=link_data.get('text', ''),
                url=link_data.get('url', '')
            ))
        
        comments = [Comment.from_dict(comment_data) for comment_data in data.get('comments', [])]
        
        return cls(
            post_id=data.get('post_id', ''),
            content=data.get('content', ''),
            timestamp=data.get('timestamp', ''),
            timestamp_estimated=data.get('timestamp_estimated', False),
            likes=data.get('likes', '0'),
            comments_count=data.get('comments_count', '0'),
            members_only=data.get('members_only', False),
            author=author,
            images=images,
            links=links,
            comments=comments
        )


@dataclass
class ArchiveMetadata:
    """Metadata for an archive session."""
    channel_id: str
    scrape_date: str
    scrape_timestamp: int
    posts_count: int
    total_comments: int = 0
    total_images: int = 0
    images_downloaded: int = 0
    config_used: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary format."""
        return {
            'channel_id': self.channel_id,
            'scrape_date': self.scrape_date,
            'scrape_timestamp': self.scrape_timestamp,
            'posts_count': self.posts_count,
            'total_comments': self.total_comments,
            'total_images': self.total_images,
            'images_downloaded': self.images_downloaded,
            'config_used': self.config_used
        }


@dataclass
class ArchiveData:
    """Complete archive data including metadata and posts."""
    metadata: ArchiveMetadata
    posts: List[Post] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert archive data to dictionary format for JSON serialization."""
        # Calculate statistics
        def count_comments_recursive(comments):
            """Recursively count comments including all nested replies."""
            total = len(comments)
            for comment in comments:
                total += count_comments_recursive(comment.replies)
            return total
        
        total_comments = sum(count_comments_recursive(post.comments) for post in self.posts)
        total_images = sum(len(post.images) for post in self.posts)
        images_downloaded = sum(
            1 for post in self.posts 
            for image in post.images 
            if image.local_path
        )
        
        # Update metadata
        self.metadata.total_comments = total_comments
        self.metadata.total_images = total_images
        self.metadata.images_downloaded = images_downloaded
        
        return {
            **self.metadata.to_dict(),
            'posts': [post.to_dict() for post in self.posts]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchiveData':
        """Create ArchiveData instance from dictionary."""
        metadata = ArchiveMetadata(
            channel_id=data.get('channel_id', ''),
            scrape_date=data.get('scrape_date', ''),
            scrape_timestamp=data.get('scrape_timestamp', 0),
            posts_count=data.get('posts_count', 0),
            total_comments=data.get('total_comments', 0),
            total_images=data.get('total_images', 0),
            images_downloaded=data.get('images_downloaded', 0),
            config_used=data.get('config_used', {})
        )
        
        posts = [Post.from_dict(post_data) for post_data in data.get('posts', [])]
        
        return cls(metadata=metadata, posts=posts)
