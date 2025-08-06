"""
Tests for data models.

This module tests the data model classes including Post, Comment, Author,
Image, Link, and archive-related models.
"""

import pytest
from datetime import datetime

from post_archiver_improved.models import (
    Author, Link, Image, Comment, Post, ArchiveMetadata, ArchiveData
)


class TestAuthor:
    """Test Author model."""
    
    def test_author_creation(self):
        """Test basic author creation."""
        author = Author(
            id="UC123456789",
            name="Test Channel",
            url="https://youtube.com/channel/UC123456789",
            thumbnail="https://example.com/avatar.jpg",
            is_verified=True,
            is_member=False
        )
        
        assert author.id == "UC123456789"
        assert author.name == "Test Channel"
        assert author.url == "https://youtube.com/channel/UC123456789"
        assert author.thumbnail == "https://example.com/avatar.jpg"
        assert author.is_verified is True
        assert author.is_member is False
    
    def test_author_defaults(self):
        """Test author with default values."""
        author = Author()
        
        assert author.id == ""
        assert author.name == ""
        assert author.url == ""
        assert author.thumbnail == ""
        assert author.is_verified is False
        assert author.is_member is False


class TestLink:
    """Test Link model."""
    
    def test_link_creation(self):
        """Test basic link creation."""
        link = Link(text="Example Link", url="https://example.com")
        
        assert link.text == "Example Link"
        assert link.url == "https://example.com"
    
    def test_link_defaults(self):
        """Test link with default values."""
        link = Link()
        
        assert link.text == ""
        assert link.url == ""


class TestImage:
    """Test Image model."""
    
    def test_image_creation(self):
        """Test basic image creation."""
        image = Image(
            src="https://example.com/image.jpg",
            local_path="/local/path/image.jpg",
            width=800,
            height=600,
            file_size=1024000
        )
        
        assert image.src == "https://example.com/image.jpg"
        assert image.local_path == "/local/path/image.jpg"
        assert image.width == 800
        assert image.height == 600
        assert image.file_size == 1024000
    
    def test_image_defaults(self):
        """Test image with default values."""
        image = Image()
        
        assert image.src == ""
        assert image.local_path is None
        assert image.width is None
        assert image.height is None
        assert image.file_size is None


class TestComment:
    """Test Comment model."""
    
    def test_comment_creation(self, sample_author):
        """Test basic comment creation."""
        comment = Comment(
            id="comment123",
            text="This is a test comment",
            like_count="5",
            timestamp="2023-01-01T12:00:00Z",
            timestamp_estimated=False,
            author=sample_author,
            is_favorited=True,
            is_pinned=False,
            reply_count="2"
        )
        
        assert comment.id == "comment123"
        assert comment.text == "This is a test comment"
        assert comment.like_count == "5"
        assert comment.timestamp == "2023-01-01T12:00:00Z"
        assert comment.timestamp_estimated is False
        assert comment.author == sample_author
        assert comment.is_favorited is True
        assert comment.is_pinned is False
        assert comment.reply_count == "2"
        assert comment.replies == []
    
    def test_comment_defaults(self):
        """Test comment with default values."""
        comment = Comment()
        
        assert comment.id == ""
        assert comment.text == ""
        assert comment.like_count == "0"
        assert comment.timestamp == ""
        assert comment.timestamp_estimated is True
        assert isinstance(comment.author, Author)
        assert comment.is_favorited is False
        assert comment.is_pinned is False
        assert comment.reply_count == "0"
        assert comment.replies == []
    
    def test_comment_to_dict(self, sample_author):
        """Test comment to dictionary conversion."""
        comment = Comment(
            id="comment123",
            text="Test comment",
            like_count="10",
            timestamp="2023-01-01T12:00:00Z",
            author=sample_author,
            is_favorited=True,
            reply_count="5"
        )
        
        comment_dict = comment.to_dict()
        
        assert comment_dict["id"] == "comment123"
        assert comment_dict["text"] == "Test comment"
        assert comment_dict["like_count"] == "10"
        assert comment_dict["timestamp"] == "2023-01-01T12:00:00Z"
        assert comment_dict["author"] == sample_author.name
        assert comment_dict["author_id"] == sample_author.id
        assert comment_dict["author_thumbnail"] == sample_author.thumbnail
        assert comment_dict["author_is_verified"] == sample_author.is_verified
        assert comment_dict["author_is_member"] == sample_author.is_member
        assert comment_dict["author_url"] == sample_author.url
        assert comment_dict["is_favorited"] is True
        assert comment_dict["reply_count"] == "5"
        assert comment_dict["replies"] == []
    
    def test_comment_from_dict(self):
        """Test comment creation from dictionary."""
        comment_data = {
            "id": "comment456",
            "text": "Another test comment",
            "like_count": "15",
            "timestamp": "2023-01-02T10:00:00Z",
            "timestamp_estimated": False,
            "author_id": "UC987654321",
            "author": "Another Channel",
            "author_url": "https://youtube.com/channel/UC987654321",
            "author_thumbnail": "https://example.com/avatar2.jpg",
            "author_is_verified": False,
            "author_is_member": True,
            "is_favorited": False,
            "is_pinned": True,
            "reply_count": "3",
            "replies": []
        }
        
        comment = Comment.from_dict(comment_data)
        
        assert comment.id == "comment456"
        assert comment.text == "Another test comment"
        assert comment.like_count == "15"
        assert comment.timestamp == "2023-01-02T10:00:00Z"
        assert comment.timestamp_estimated is False
        assert comment.author.id == "UC987654321"
        assert comment.author.name == "Another Channel"
        assert comment.author.url == "https://youtube.com/channel/UC987654321"
        assert comment.author.thumbnail == "https://example.com/avatar2.jpg"
        assert comment.author.is_verified is False
        assert comment.author.is_member is True
        assert comment.is_favorited is False
        assert comment.is_pinned is True
        assert comment.reply_count == "3"
        assert comment.replies == []
    
    def test_comment_with_replies(self, sample_author):
        """Test comment with nested replies."""
        reply1 = Comment(
            id="reply1",
            text="First reply",
            author=sample_author
        )
        reply2 = Comment(
            id="reply2",
            text="Second reply",
            author=sample_author
        )
        
        main_comment = Comment(
            id="main_comment",
            text="Main comment",
            author=sample_author,
            replies=[reply1, reply2]
        )
        
        assert len(main_comment.replies) == 2
        assert main_comment.replies[0].id == "reply1"
        assert main_comment.replies[1].id == "reply2"
        
        # Test to_dict with replies
        comment_dict = main_comment.to_dict()
        assert len(comment_dict["replies"]) == 2
        assert comment_dict["replies"][0]["id"] == "reply1"
        assert comment_dict["replies"][1]["id"] == "reply2"


class TestPost:
    """Test Post model."""
    
    def test_post_creation(self, sample_author, sample_image, sample_link, sample_comment):
        """Test basic post creation."""
        post = Post(
            post_id="post123",
            content="This is a test post",
            timestamp="2023-01-01T10:00:00Z",
            timestamp_estimated=False,
            likes="100",
            comments_count="25",
            members_only=True,
            author=sample_author,
            images=[sample_image],
            links=[sample_link],
            comments=[sample_comment]
        )
        
        assert post.post_id == "post123"
        assert post.content == "This is a test post"
        assert post.timestamp == "2023-01-01T10:00:00Z"
        assert post.timestamp_estimated is False
        assert post.likes == "100"
        assert post.comments_count == "25"
        assert post.members_only is True
        assert post.author == sample_author
        assert len(post.images) == 1
        assert len(post.links) == 1
        assert len(post.comments) == 1
    
    def test_post_defaults(self):
        """Test post with default values."""
        post = Post()
        
        assert post.post_id == ""
        assert post.content == ""
        assert post.timestamp == ""
        assert post.timestamp_estimated is False
        assert post.likes == "0"
        assert post.comments_count == "0"
        assert post.members_only is False
        assert isinstance(post.author, Author)
        assert post.images == []
        assert post.links == []
        assert post.comments == []
    
    def test_post_to_dict(self, sample_author, sample_image, sample_link, sample_comment):
        """Test post to dictionary conversion."""
        post = Post(
            post_id="post456",
            content="Test post content",
            timestamp="2023-01-01T15:00:00Z",
            likes="50",
            comments_count="10",
            author=sample_author,
            images=[sample_image],
            links=[sample_link],
            comments=[sample_comment]
        )
        
        post_dict = post.to_dict()
        
        assert post_dict["post_id"] == "post456"
        assert post_dict["content"] == "Test post content"
        assert post_dict["timestamp"] == "2023-01-01T15:00:00Z"
        assert post_dict["likes"] == "50"
        assert post_dict["comments_count"] == "10"
        assert post_dict["author"] == sample_author.name
        assert post_dict["author_id"] == sample_author.id
        assert post_dict["author_url"] == sample_author.url
        assert post_dict["author_thumbnail"] == sample_author.thumbnail
        assert post_dict["author_is_verified"] == sample_author.is_verified
        assert post_dict["author_is_member"] == sample_author.is_member
        assert len(post_dict["images"]) == 1
        assert len(post_dict["links"]) == 1
        assert len(post_dict["comments"]) == 1
        
        # Check image data
        image_dict = post_dict["images"][0]
        assert image_dict["src"] == sample_image.src
        assert image_dict["local_path"] == sample_image.local_path
        assert image_dict["width"] == sample_image.width
        assert image_dict["height"] == sample_image.height
        assert image_dict["file_size"] == sample_image.file_size
        
        # Check link data
        link_dict = post_dict["links"][0]
        assert link_dict["text"] == sample_link.text
        assert link_dict["url"] == sample_link.url
        
        # Check comment data
        comment_dict = post_dict["comments"][0]
        assert comment_dict["id"] == sample_comment.id
        assert comment_dict["text"] == sample_comment.text
    
    def test_post_from_dict(self):
        """Test post creation from dictionary."""
        post_data = {
            "post_id": "post789",
            "content": "Post from dict",
            "timestamp": "2023-01-03T08:00:00Z",
            "timestamp_estimated": True,
            "likes": "75",
            "comments_count": "15",
            "members_only": False,
            "author": "Test Author",
            "author_id": "UC111222333",
            "author_url": "https://youtube.com/channel/UC111222333",
            "author_thumbnail": "https://example.com/avatar3.jpg",
            "author_is_verified": True,
            "author_is_member": False,
            "images": [
                {
                    "src": "https://example.com/test.jpg",
                    "local_path": "/local/test.jpg",
                    "width": 1024,
                    "height": 768,
                    "file_size": 2048000
                }
            ],
            "links": [
                {
                    "text": "Test Link",
                    "url": "https://test.example.com"
                }
            ],
            "comments": []
        }
        
        post = Post.from_dict(post_data)
        
        assert post.post_id == "post789"
        assert post.content == "Post from dict"
        assert post.timestamp == "2023-01-03T08:00:00Z"
        assert post.timestamp_estimated is True
        assert post.likes == "75"
        assert post.comments_count == "15"
        assert post.members_only is False
        assert post.author.name == "Test Author"
        assert post.author.id == "UC111222333"
        assert post.author.url == "https://youtube.com/channel/UC111222333"
        assert post.author.thumbnail == "https://example.com/avatar3.jpg"
        assert post.author.is_verified is True
        assert post.author.is_member is False
        assert len(post.images) == 1
        assert len(post.links) == 1
        assert len(post.comments) == 0
        
        # Check image
        image = post.images[0]
        assert image.src == "https://example.com/test.jpg"
        assert image.local_path == "/local/test.jpg"
        assert image.width == 1024
        assert image.height == 768
        assert image.file_size == 2048000
        
        # Check link
        link = post.links[0]
        assert link.text == "Test Link"
        assert link.url == "https://test.example.com"


class TestArchiveMetadata:
    """Test ArchiveMetadata model."""
    
    def test_metadata_creation(self):
        """Test basic metadata creation."""
        metadata = ArchiveMetadata(
            channel_id="UC123456789",
            scrape_date="2023-01-01T12:00:00Z",
            scrape_timestamp=1672574400,
            posts_count=10,
            total_comments=50,
            total_images=15,
            images_downloaded=12,
            config_used={"max_posts": 10, "extract_comments": True}
        )
        
        assert metadata.channel_id == "UC123456789"
        assert metadata.scrape_date == "2023-01-01T12:00:00Z"
        assert metadata.scrape_timestamp == 1672574400
        assert metadata.posts_count == 10
        assert metadata.total_comments == 50
        assert metadata.total_images == 15
        assert metadata.images_downloaded == 12
        assert metadata.config_used == {"max_posts": 10, "extract_comments": True}
    
    def test_metadata_defaults(self):
        """Test metadata with default values."""
        metadata = ArchiveMetadata(
            channel_id="UC123456789",
            scrape_date="2023-01-01T12:00:00Z",
            scrape_timestamp=1672574400,
            posts_count=5
        )
        
        assert metadata.total_comments == 0
        assert metadata.total_images == 0
        assert metadata.images_downloaded == 0
        assert metadata.config_used == {}
    
    def test_metadata_to_dict(self):
        """Test metadata to dictionary conversion."""
        metadata = ArchiveMetadata(
            channel_id="UC987654321",
            scrape_date="2023-01-02T10:00:00Z",
            scrape_timestamp=1672660800,
            posts_count=8,
            total_comments=30,
            total_images=5,
            images_downloaded=5,
            config_used={"max_posts": 20}
        )
        
        metadata_dict = metadata.to_dict()
        
        assert metadata_dict["channel_id"] == "UC987654321"
        assert metadata_dict["scrape_date"] == "2023-01-02T10:00:00Z"
        assert metadata_dict["scrape_timestamp"] == 1672660800
        assert metadata_dict["posts_count"] == 8
        assert metadata_dict["total_comments"] == 30
        assert metadata_dict["total_images"] == 5
        assert metadata_dict["images_downloaded"] == 5
        assert metadata_dict["config_used"] == {"max_posts": 20}


class TestArchiveData:
    """Test ArchiveData model."""
    
    def test_archive_data_creation(self, sample_archive_metadata, sample_post):
        """Test basic archive data creation."""
        archive_data = ArchiveData(
            metadata=sample_archive_metadata,
            posts=[sample_post]
        )
        
        assert archive_data.metadata == sample_archive_metadata
        assert len(archive_data.posts) == 1
        assert archive_data.posts[0] == sample_post
    
    def test_archive_data_defaults(self, sample_archive_metadata):
        """Test archive data with default values."""
        archive_data = ArchiveData(metadata=sample_archive_metadata)
        
        assert archive_data.posts == []
    
    def test_archive_data_to_dict(self, sample_archive_metadata, sample_post):
        """Test archive data to dictionary conversion."""
        archive_data = ArchiveData(
            metadata=sample_archive_metadata,
            posts=[sample_post]
        )
        
        archive_dict = archive_data.to_dict()
        
        # Check that metadata fields are at top level
        assert archive_dict["channel_id"] == sample_archive_metadata.channel_id
        assert archive_dict["scrape_date"] == sample_archive_metadata.scrape_date
        assert archive_dict["scrape_timestamp"] == sample_archive_metadata.scrape_timestamp
        assert archive_dict["posts_count"] == sample_archive_metadata.posts_count
        
        # Check that posts are included
        assert "posts" in archive_dict
        assert len(archive_dict["posts"]) == 1
        assert archive_dict["posts"][0]["post_id"] == sample_post.post_id
    
    def test_archive_data_statistics_calculation(self):
        """Test that archive data calculates statistics correctly."""
        # Create test data with known statistics
        author = Author(id="UC123", name="Test")
        
        comment1 = Comment(id="c1", text="Comment 1", author=author)
        comment2 = Comment(id="c2", text="Comment 2", author=author)
        reply1 = Comment(id="r1", text="Reply 1", author=author)
        comment1.replies = [reply1]
        
        image1 = Image(src="https://example.com/img1.jpg", local_path="/local/img1.jpg")
        image2 = Image(src="https://example.com/img2.jpg")  # No local path
        image3 = Image(src="https://example.com/img3.jpg", local_path="/local/img3.jpg")
        
        post1 = Post(
            post_id="p1",
            author=author,
            comments=[comment1, comment2],
            images=[image1, image2]
        )
        post2 = Post(
            post_id="p2",
            author=author,
            comments=[],
            images=[image3]
        )
        
        metadata = ArchiveMetadata(
            channel_id="UC123",
            scrape_date="2023-01-01T12:00:00Z",
            scrape_timestamp=1672574400,
            posts_count=2
        )
        
        archive_data = ArchiveData(
            metadata=metadata,
            posts=[post1, post2]
        )
        
        archive_dict = archive_data.to_dict()
        
        # Verify calculated statistics
        # Total comments: 2 comments + 1 reply = 3
        assert archive_dict["total_comments"] == 3
        # Total images: 2 + 1 = 3
        assert archive_dict["total_images"] == 3
        # Downloaded images: 2 (only img1 and img3 have local_path)
        assert archive_dict["images_downloaded"] == 2
    
    def test_archive_data_from_dict(self):
        """Test archive data creation from dictionary."""
        archive_dict = {
            "channel_id": "UC555666777",
            "scrape_date": "2023-01-04T14:00:00Z",
            "scrape_timestamp": 1672833600,
            "posts_count": 3,
            "total_comments": 20,
            "total_images": 8,
            "images_downloaded": 6,
            "config_used": {"max_posts": 50},
            "posts": [
                {
                    "post_id": "test_post",
                    "content": "Test content",
                    "timestamp": "2023-01-04T13:00:00Z",
                    "timestamp_estimated": False,
                    "likes": "25",
                    "comments_count": "5",
                    "members_only": False,
                    "author": "Test Channel",
                    "author_id": "UC555666777",
                    "author_url": "https://youtube.com/channel/UC555666777",
                    "author_thumbnail": "https://example.com/avatar.jpg",
                    "author_is_verified": False,
                    "author_is_member": False,
                    "images": [],
                    "links": [],
                    "comments": []
                }
            ]
        }
        
        archive_data = ArchiveData.from_dict(archive_dict)
        
        assert archive_data.metadata.channel_id == "UC555666777"
        assert archive_data.metadata.scrape_date == "2023-01-04T14:00:00Z"
        assert archive_data.metadata.scrape_timestamp == 1672833600
        assert archive_data.metadata.posts_count == 3
        assert archive_data.metadata.total_comments == 20
        assert archive_data.metadata.total_images == 8
        assert archive_data.metadata.images_downloaded == 6
        assert archive_data.metadata.config_used == {"max_posts": 50}
        assert len(archive_data.posts) == 1
        assert archive_data.posts[0].post_id == "test_post"
        assert archive_data.posts[0].content == "Test content"


if __name__ == "__main__":
    pytest.main([__file__])
