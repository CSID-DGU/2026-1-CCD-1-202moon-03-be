from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("username은 필수입니다.")
        if not email:
            raise ValueError("email은 필수입니다.")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=15)
    avatar_type = models.CharField(max_length=50, default="character_1")
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    stimulation_level = models.IntegerField(default=1)  # 1=low 2=medium 3=high
    is_tutorial_done = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "user"

    def __str__(self):
        return self.username


class UserSetting(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="setting"
    )
    fidget_toggle_key = models.CharField(max_length=20, default="alt")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_setting"