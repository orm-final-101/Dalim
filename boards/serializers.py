from rest_framework import serializers
from .models import Post, Comment, Like
from config.constants import CLASSIFICATION_CHOICES, CATEGORY_CHOICES


# 댓글 수정 및 작성
class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "author", "post", "contents"]


# 게시물 전체 보기
class PostListSerializer(serializers.ModelSerializer):
    author_nickname = serializers.CharField(source="author.nickname")
    comment_count = serializers.SerializerMethodField()
    thumbnail_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "author_id",
            "author_nickname",
            "title",
            "thumbnail_image",
            "post_classification",
            "category",
            "view_count",
            "comment_count",
            "created_at",
            "updated_at",
        ]

        order_by = ["-created_at"]

    def get_comment_count(self, obj):
        return obj.posted_comments.count()

    def get_delete_message(self, obj):
        return "게시글을 삭제했습니다."


# 게시글 상세 보기
class PostDetailSerializer(serializers.ModelSerializer):
    author_nickname = serializers.CharField(source="author.nickname", read_only=True)
    likes = serializers.SerializerMethodField()
    thumbnail_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "author_id",
            "author_nickname",
            "title",
            "contents",
            "thumbnail_image",
            "post_classification",
            "category",
            "view_count",
            "created_at",
            "updated_at",
            "likes",
        ]

    def get_likes(self, obj):
        user = self.context["request"].user
        if user.is_authenticated:
            is_liked = Like.objects.filter(post=obj, author=user).exists()
            return {"count": obj.likes.count(), "is_liked": is_liked}
        return {"count": obj.likes.count(), "is_liked": False}


# 게시글 수정
class PostUpdateSerializer(serializers.ModelSerializer):
    thumbnail_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Post
        fields = [
            "title",
            "contents",
            "thumbnail_image",
            "post_classification",
            "category",
        ]

    def update(self, instance, validated_data):
        instance.title = validated_data.get("title", instance.title)
        instance.contents = validated_data.get("contents", instance.contents)
        instance.thumbnail_image = validated_data.get(
            "thumbnail_image", instance.thumbnail_image
        )
        instance.post_classification = validated_data.get(
            "post_classification", instance.post_classification
        )
        instance.category = validated_data.get("category", instance.category)
        instance.save()
        return instance


# 게시글 작성
class PostCreateSerializer(serializers.ModelSerializer):
    thumbnail_image = serializers.ImageField(required=False, allow_null=True)
    post_classification = serializers.ChoiceField(
        required=True, choices=CLASSIFICATION_CHOICES
    )
    category = serializers.ChoiceField(required=True, choices=CATEGORY_CHOICES)

    class Meta:
        model = Post
        fields = [
            "title",
            "contents",
            "category",
            "post_classification",
            "thumbnail_image",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        if request.user.is_authenticated:
            validated_data["author"] = request.user
            post = Post.objects.create(**validated_data)
            return post
        else:
            raise serializers.ValidationError(
                "User must be authenticated to create a post."
            )

    def validate_post_classification(self, value):
        if value not in [choice[0] for choice in CLASSIFICATION_CHOICES]:
            raise serializers.ValidationError("Invalid post classification.")
        return value

    def validate_category(self, value):
        if value not in [choice[0] for choice in CATEGORY_CHOICES]:
            raise serializers.ValidationError("Invalid category.")
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["id"] = instance.id
        return representation


# 댓글
class CommentSerializer(serializers.ModelSerializer):
    author_nickname = serializers.CharField(source="author.nickname", read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author_id", "author_nickname", "contents", "created_at"]

    def save(self, **kwargs):
        # 로그인된 사용자 정보 설정
        if self.context["request"].user.is_authenticated:
            kwargs["author"] = self.context["request"].user
        else:
            raise serializers.ValidationError("로그인이 필요합니다.")

        kwargs["post"] = Post.objects.get(id=self.context["view"].kwargs["post_id"])
        return super().save(**kwargs)

    def get_queryset(self):
        post_id = self.context["view"].kwargs["post_id"]
        return Comment.objects.filter(post_id=post_id)


# 유저 오픈프로필에서 내가 작성한 덧글 볼 때 사용
class ProfileCommentSerializer(serializers.ModelSerializer):
    post = serializers.SerializerMethodField()
    comment = serializers.CharField(source="contents")

    def get_post(self, obj):
        return {
            "id": obj.post.id,
            "title": obj.post.title,
            "author": obj.post.author.nickname,
        }

    class Meta:
        model = Comment
        fields = ["post", "comment"]


# 유저 오픈프로필에서 내가 좋아한 게시글 볼 때 사용
class ProfileLikedPostSerializer(serializers.ModelSerializer):
    post_id = serializers.IntegerField(source="post.id")
    title = serializers.CharField(source="post.title")
    author = serializers.CharField(source="post.author.nickname")
    comment_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()

    def get_comment_count(self, obj):
        return Comment.objects.filter(post=obj.post).count()

    def get_like_count(self, obj):
        return obj.post.likes.count()

    class Meta:
        model = Post
        fields = ["post_id", "title", "author", "comment_count", "like_count"]
