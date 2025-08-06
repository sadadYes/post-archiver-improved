"""
Tests for data extractors.

This module tests the PostExtractor and CommentExtractor classes
responsible for parsing YouTube API responses.
"""

import pytest
from unittest.mock import Mock, patch

from post_archiver_improved.extractors import PostExtractor, CommentExtractor
from post_archiver_improved.models import Post, Comment, Author, Image, Link
from post_archiver_improved.exceptions import ParseError


class TestPostExtractor:
    """Test PostExtractor class."""
    
    def test_extract_text_content_basic(self):
        """Test basic text content extraction."""
        content_runs = [
            {"text": "Hello "},
            {"text": "world!"}
        ]
        
        result = PostExtractor.extract_text_content(content_runs)
        assert result == "Hello world!"
    
    def test_extract_text_content_empty(self):
        """Test text content extraction with empty input."""
        assert PostExtractor.extract_text_content([]) == ""
        assert PostExtractor.extract_text_content(None) == ""
    
    def test_extract_text_content_missing_text(self):
        """Test text content extraction with missing text fields."""
        content_runs = [
            {"text": "Hello "},
            {"url": "https://example.com"},  # No text field
            {"text": "world!"}
        ]
        
        result = PostExtractor.extract_text_content(content_runs)
        assert result == "Hello world!"
    
    def test_extract_author_info_complete(self):
        """Test author information extraction with complete data."""
        post_renderer = {
            "authorText": {"runs": [{"text": "Test Channel"}]},
            "authorEndpoint": {
                "browseEndpoint": {
                    "browseId": "UC123456789",
                    "canonicalBaseUrl": "/channel/UC123456789"
                }
            },
            "authorThumbnail": {
                "thumbnails": [
                    {"url": "https://example.com/avatar.jpg", "width": 88, "height": 88}
                ]
            },
            "authorCommentBadge": {
                "authorCommentBadgeRenderer": {
                    "icon": {"iconType": "CHECK_CIRCLE_THICK"}
                }
            }
        }
        
        author = PostExtractor._extract_author_info(post_renderer)
        
        assert author.name == "Test Channel"
        assert author.id == "UC123456789"
        assert "channel/UC123456789" in author.url
        assert author.thumbnail == "https://example.com/avatar.jpg"
        assert author.is_verified is True
    
    def test_extract_author_info_minimal(self):
        """Test author information extraction with minimal data."""
        post_renderer = {
            "authorText": {"runs": [{"text": "Basic Channel"}]}
        }
        
        author = PostExtractor._extract_author_info(post_renderer)
        
        assert author.name == "Basic Channel"
        assert author.id == ""
        assert author.url == ""
        assert author.thumbnail == ""
        assert author.is_verified is False
    
    def test_extract_author_info_empty(self):
        """Test author information extraction with empty data."""
        author = PostExtractor._extract_author_info({})
        
        assert author.name == ""
        assert author.id == ""
        assert author.url == ""
        assert author.thumbnail == ""
        assert author.is_verified is False
    
    def test_extract_images_basic(self):
        """Test image extraction from post."""
        post_renderer = {
            "backstageAttachment": {
                "backstageImageRenderer": {
                    "image": {
                        "thumbnails": [
                            {"url": "https://example.com/small.jpg", "width": 200, "height": 150},
                            {"url": "https://example.com/large.jpg", "width": 800, "height": 600}
                        ]
                    }
                }
            }
        }
        
        images = PostExtractor._extract_images(post_renderer)
        
        assert len(images) == 1
        image = images[0]
        assert image.src == "https://example.com/small.jpg=s0"  # Should use first URL with =s0 for best resolution
        assert image.width == 800  # Should get dimensions from largest thumbnail
        assert image.height == 600
        assert image.local_path is None
    
    def test_extract_images_multiple_attachments(self):
        """Test extraction of multiple images."""
        # Note: This tests the structure we expect to handle multiple images
        post_renderer = {
            "backstageAttachment": {
                "postMultiImageRenderer": {
                    "images": [
                        {
                            "backstageImageRenderer": {
                                "image": {
                                    "thumbnails": [
                                        {"url": "https://example.com/image1.jpg", "width": 400, "height": 300}
                                    ]
                                }
                            }
                        },
                        {
                            "backstageImageRenderer": {
                                "image": {
                                    "thumbnails": [
                                        {"url": "https://example.com/image2.jpg", "width": 500, "height": 400}
                                    ]
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        images = PostExtractor._extract_images(post_renderer)
        
        assert len(images) == 2
        assert images[0].src == "https://example.com/image1.jpg=s0"
        assert images[1].src == "https://example.com/image2.jpg=s0"
    
    def test_extract_images_no_images(self):
        """Test image extraction when no images present."""
        post_renderer = {}
        images = PostExtractor._extract_images(post_renderer)
        assert images == []
    
    def test_extract_links_basic(self):
        """Test link extraction from post content."""
        content_runs = [
            {"text": "Check out "},
            {
                "text": "this link",
                "navigationEndpoint": {
                    "urlEndpoint": {"url": "https://example.com"}
                }
            },
            {"text": " for more info."}
        ]
        
        links = PostExtractor._extract_links(content_runs)
        
        assert len(links) == 1
        link = links[0]
        assert link.text == "this link"
        assert link.url == "https://example.com"
    
    def test_extract_links_multiple(self):
        """Test extraction of multiple links."""
        content_runs = [
            {"text": "Visit "},
            {
                "text": "site one",
                "navigationEndpoint": {
                    "urlEndpoint": {"url": "https://one.example.com"}
                }
            },
            {"text": " and "},
            {
                "text": "site two",
                "navigationEndpoint": {
                    "urlEndpoint": {"url": "https://two.example.com"}
                }
            }
        ]
        
        links = PostExtractor._extract_links(content_runs)
        
        assert len(links) == 2
        assert links[0].text == "site one"
        assert links[0].url == "https://one.example.com"
        assert links[1].text == "site two"
        assert links[1].url == "https://two.example.com"
    
    def test_extract_links_no_links(self):
        """Test link extraction when no links present."""
        content_runs = [
            {"text": "Just plain text"},
            {"text": " with no links"}
        ]
        
        links = PostExtractor._extract_links(content_runs)
        assert links == []
    
    def test_extract_post_complete(self):
        """Test complete post extraction."""
        post_data = {
            "backstagePostRenderer": {
                "postId": "post123",
                "contentText": {
                    "runs": [
                        {"text": "Test post content with "},
                        {
                            "text": "a link",
                            "navigationEndpoint": {
                                "urlEndpoint": {"url": "https://example.com"}
                            }
                        }
                    ]
                },
                "publishedTimeText": {"runs": [{"text": "2 hours ago"}]},
                "voteCount": {"runs": [{"text": "42"}]},
                "voteStatus": "LIKE",
                "authorText": {"runs": [{"text": "Test Channel"}]},
                "authorEndpoint": {
                    "browseEndpoint": {
                        "browseId": "UC123456789"
                    }
                },
                "backstageAttachment": {
                    "backstageImageRenderer": {
                        "image": {
                            "thumbnails": [
                                {"url": "https://example.com/image.jpg", "width": 800, "height": 600}
                            ]
                        }
                    }
                },
                "actionButtons": {
                    "commentActionButtonsRenderer": {
                        "replyButton": {
                            "buttonRenderer": {
                                "text": {"runs": [{"text": "15"}]}
                            }
                        }
                    }
                }
            }
        }
        
        post = PostExtractor.extract_post(post_data)
        
        assert post.post_id == "post123"
        assert post.content == "Test post content with a link"
        assert post.timestamp == "2 hours ago"
        assert post.likes == "42"
        assert post.comments_count == "15"
        assert post.author.name == "Test Channel"
        assert post.author.id == "UC123456789"
        assert len(post.images) == 1
        assert len(post.links) == 1
        assert post.images[0].src == "https://example.com/image.jpg=s0"
        assert post.links[0].text == "a link"
        assert post.links[0].url == "https://example.com"
    
    def test_extract_post_minimal(self):
        """Test post extraction with minimal data."""
        post_data = {
            "backstagePostRenderer": {
                "postId": "minimal_post",
                "contentText": {"runs": [{"text": "Basic post"}]}
            }
        }
        
        post = PostExtractor.extract_post(post_data)
        
        assert post.post_id == "minimal_post"
        assert post.content == "Basic post"
        assert post.timestamp == ""
        assert post.likes == "0"
        assert post.comments_count == "0"
        assert post.images == []
        assert post.links == []
    
    def test_extract_post_invalid_structure(self):
        """Test post extraction with invalid structure."""
        invalid_data = {"invalidRenderer": {}}
        
        with pytest.raises(ParseError):
            PostExtractor.extract_post(invalid_data)
    
    def test_extract_post_missing_post_id(self):
        """Test post extraction with missing post ID."""
        post_data = {
            "backstagePostRenderer": {
                "contentText": {"runs": [{"text": "Post without ID"}]}
            }
        }
        
        post = PostExtractor.extract_post(post_data)
        assert post.post_id == ""  # Should handle gracefully
    
    def test_extract_members_only_post(self):
        """Test extraction of members-only posts."""
        post_data = {
            "backstagePostRenderer": {
                "postId": "members_post",
                "contentText": {"runs": [{"text": "Members only content"}]},
                "sponsorsOnlyBadge": {
                    "sponsorsOnlyBadgeRenderer": {
                        "label": {"runs": [{"text": "Members only"}]}
                    }
                }
            }
        }
        
        post = PostExtractor.extract_post(post_data)
        
        assert post.post_id == "members_post"
        assert post.members_only is True


class TestCommentExtractor:
    """Test CommentExtractor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_api = Mock()
        self.extractor = CommentExtractor(self.mock_api)
    
    def test_extract_comment_basic(self):
        """Test basic comment extraction."""
        comment_data = {
            "commentRenderer": {
                "commentId": "comment123",
                "contentText": {"runs": [{"text": "Great post!"}]},
                "publishedTimeText": {"runs": [{"text": "1 day ago"}]},
                "voteCount": {"runs": [{"text": "5"}]},
                "authorText": {"runs": [{"text": "Commenter"}]},
                "authorEndpoint": {
                    "browseEndpoint": {"browseId": "UC987654321"}
                },
                "authorThumbnail": {
                    "thumbnails": [{"url": "https://example.com/commenter.jpg"}]
                },
                "replyCount": {"runs": [{"text": "2"}]}
            }
        }
        
        comment = CommentExtractor.extract_comment(comment_data)
        
        assert comment.id == "comment123"
        assert comment.text == "Great post!"
        assert comment.timestamp == "1 day ago"
        assert comment.like_count == "5"
        assert comment.author.name == "Commenter"
        assert comment.author.id == "UC987654321"
        assert comment.reply_count == "2"
        assert comment.replies == []
    
    def test_extract_comment_with_badges(self):
        """Test comment extraction with author badges."""
        comment_data = {
            "commentRenderer": {
                "commentId": "verified_comment",
                "contentText": {"runs": [{"text": "Official comment"}]},
                "authorText": {"runs": [{"text": "Verified User"}]},
                "authorCommentBadge": {
                    "authorCommentBadgeRenderer": {
                        "icon": {"iconType": "CHECK_CIRCLE_THICK"}
                    }
                },
                "sponsorCommentBadge": {
                    "sponsorCommentBadgeRenderer": {
                        "text": {"runs": [{"text": "Member"}]}
                    }
                }
            }
        }
        
        comment = CommentExtractor.extract_comment(comment_data)
        
        assert comment.author.is_verified is True
        assert comment.author.is_member is True
    
    def test_extract_comment_pinned_favorited(self):
        """Test extraction of pinned and favorited comments."""
        comment_data = {
            "commentRenderer": {
                "commentId": "special_comment",
                "contentText": {"runs": [{"text": "Pinned comment"}]},
                "pinnedCommentBadge": {
                    "pinnedCommentBadgeRenderer": {
                        "label": {"runs": [{"text": "Pinned by creator"}]}
                    }
                },
                "isLiked": True
            }
        }
        
        comment = CommentExtractor.extract_comment(comment_data)
        
        assert comment.is_pinned is True
        assert comment.is_favorited is True
    
    def test_extract_comment_minimal(self):
        """Test comment extraction with minimal data."""
        comment_data = {
            "commentRenderer": {
                "commentId": "minimal_comment",
                "contentText": {"runs": [{"text": "Basic comment"}]}
            }
        }
        
        comment = CommentExtractor.extract_comment(comment_data)
        
        assert comment.id == "minimal_comment"
        assert comment.text == "Basic comment"
        assert comment.timestamp == ""
        assert comment.like_count == "0"
        assert comment.reply_count == "0"
        assert comment.author.name == ""
    
    def test_extract_comment_invalid_structure(self):
        """Test comment extraction with invalid structure."""
        invalid_data = {"invalidRenderer": {}}
        
        with pytest.raises(ParseError):
            CommentExtractor.extract_comment(invalid_data)
    
    def test_extract_comments_from_response(self):
        """Test extraction of multiple comments from API response."""
        response_data = {
            "frameworkUpdates": {
                "entityBatchUpdate": {
                    "mutations": [
                        {
                            "payload": {
                                "commentEntityPayload": {
                                    "properties": {
                                        "content": {
                                            "runs": [{"text": "First comment"}]
                                        }
                                    },
                                    "key": "comment1"
                                }
                            }
                        },
                        {
                            "payload": {
                                "commentEntityPayload": {
                                    "properties": {
                                        "content": {
                                            "runs": [{"text": "Second comment"}]
                                        }
                                    },
                                    "key": "comment2"
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        comments = CommentExtractor.extract_comments_from_response(response_data)
        
        assert len(comments) == 2
        assert comments[0].text == "First comment"
        assert comments[1].text == "Second comment"
    
    def test_extract_comments_empty_response(self):
        """Test comment extraction from empty response."""
        empty_response = {}
        comments = CommentExtractor.extract_comments_from_response(empty_response)
        assert comments == []
    
    def test_extract_replies_basic(self):
        """Test extraction of comment replies."""
        reply_data = [
            {
                "commentRenderer": {
                    "commentId": "reply1",
                    "contentText": {"runs": [{"text": "First reply"}]},
                    "authorText": {"runs": [{"text": "Replier1"}]}
                }
            },
            {
                "commentRenderer": {
                    "commentId": "reply2",
                    "contentText": {"runs": [{"text": "Second reply"}]},
                    "authorText": {"runs": [{"text": "Replier2"}]}
                }
            }
        ]
        
        replies = CommentExtractor.extract_replies(reply_data)
        
        assert len(replies) == 2
        assert replies[0].id == "reply1"
        assert replies[0].text == "First reply"
        assert replies[0].author.name == "Replier1"
        assert replies[1].id == "reply2"
        assert replies[1].text == "Second reply"
        assert replies[1].author.name == "Replier2"
    
    def test_extract_replies_empty(self):
        """Test reply extraction from empty data."""
        replies = CommentExtractor.extract_replies([])
        assert replies == []
    
    def test_extract_replies_invalid_data(self):
        """Test reply extraction with invalid data."""
        invalid_reply_data = [
            {"invalidRenderer": {}},
            {
                "commentRenderer": {
                    "commentId": "valid_reply",
                    "contentText": {"runs": [{"text": "Valid reply"}]}
                }
            }
        ]
        
        replies = CommentExtractor.extract_replies(invalid_reply_data)
        
        # Should skip invalid items and process valid ones
        assert len(replies) == 1
        assert replies[0].id == "valid_reply"
        assert replies[0].text == "Valid reply"


class TestExtractorErrorHandling:
    """Test error handling in extractors."""
    
    def test_post_extractor_with_malformed_data(self):
        """Test post extractor with malformed data."""
        malformed_data = {
            "backstagePostRenderer": {
                "postId": "test_post",
                "contentText": "not_a_dict",  # Should be dict with runs
                "voteCount": {"runs": None}   # Null runs
            }
        }
        
        # Should handle gracefully without crashing
        post = PostExtractor.extract_post(malformed_data)
        assert post.post_id == "test_post"
        assert post.content == ""  # Should fallback to empty string
    
    def test_comment_extractor_with_malformed_data(self):
        """Test comment extractor with malformed data."""
        malformed_data = {
            "commentRenderer": {
                "commentId": "test_comment",
                "contentText": None,  # Null content
                "authorText": {"runs": "not_a_list"}  # Should be list
            }
        }
        
        # Should handle gracefully
        comment = CommentExtractor.extract_comment(malformed_data)
        assert comment.id == "test_comment"
        assert comment.text == ""
        assert comment.author.name == ""
    
    def test_extractor_with_missing_required_fields(self):
        """Test extractors with missing required fields."""
        # Post without backstagePostRenderer
        post_data = {"someOtherRenderer": {}}
        with pytest.raises(ParseError):
            PostExtractor.extract_post(post_data)
        
        # Comment without commentRenderer
        comment_data = {"someOtherRenderer": {}}
        with pytest.raises(ParseError):
            CommentExtractor.extract_comment(comment_data)
    
    def test_extractor_unicode_handling(self):
        """Test extractors with Unicode content."""
        unicode_post_data = {
            "backstagePostRenderer": {
                "postId": "unicode_post",
                "contentText": {
                    "runs": [
                        {"text": "Hello 世界! "},
                        {"text": "🎥 Тест 📹"}
                    ]
                },
                "authorText": {"runs": [{"text": "测试频道"}]}
            }
        }
        
        post = PostExtractor.extract_post(unicode_post_data)
        
        assert post.content == "Hello 世界! 🎥 Тест 📹"
        assert post.author.name == "测试频道"
    
    def test_extractor_large_content(self):
        """Test extractors with large content."""
        # Create large content
        large_content = [{"text": "x" * 1000} for _ in range(100)]
        
        large_post_data = {
            "backstagePostRenderer": {
                "postId": "large_post",
                "contentText": {"runs": large_content}
            }
        }
        
        post = PostExtractor.extract_post(large_post_data)
        
        assert len(post.content) == 100000  # 100 * 1000
        assert post.post_id == "large_post"


if __name__ == "__main__":
    pytest.main([__file__])
