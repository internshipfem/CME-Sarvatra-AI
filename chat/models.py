import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    employee_id = models.CharField(max_length=50, blank=True, default='')
    department = models.CharField(max_length=100, blank=True, default='Combat Engineering Wing')
    rank = models.CharField(max_length=50, blank=True, default='')
    appointment = models.CharField(max_length=100, blank=True, default='')
    authority = models.CharField(max_length=100, blank=True, default='')
    signature_style = models.CharField(max_length=50, blank=True, default='military')
    signature_text = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        display = full_name if full_name else self.user.username
        if self.employee_id:
            return f"{display} (ID: {self.employee_id})"
        return display


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            UserProfile.objects.create(user=instance)


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=255, default='New Chat')
    model_name = models.CharField(max_length=100, default='llama3:latest')
    system_prompt = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.model_name})"


class UploadedFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files')
    conversation = models.ForeignKey(
        Conversation, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_files'
    )
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    original_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    extracted_text = models.TextField(blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.original_name

    def format_size(self):
        bytes_val = self.file_size
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        else:
            return f"{bytes_val / (1024 * 1024):.1f} MB"


class Message(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    )

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    
    # Bottleneck / Performance Telemetry
    response_time = models.FloatField(null=True, blank=True, help_text="Total response time in seconds")
    eval_count = models.IntegerField(null=True, blank=True, help_text="Total tokens evaluated")
    eval_duration = models.FloatField(null=True, blank=True, help_text="Token generation duration in seconds")
    load_duration = models.FloatField(null=True, blank=True, help_text="Model load duration in seconds")
    tokens_per_second = models.FloatField(null=True, blank=True, help_text="Inference speed")

    attached_files = models.ManyToManyField(UploadedFile, blank=True, related_name='messages')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role.capitalize()}: {self.content[:30]}..."


class GeneratedDocument(models.Model):
    """Tracks AI-generated office documents."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='generated_documents')
    conversation = models.ForeignKey(
        Conversation, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_documents'
    )

    # What was generated
    document_type = models.CharField(max_length=50)     # formal_letter, office_memo, etc.
    title = models.CharField(max_length=255)
    fields_json = models.TextField(default='{}')        # Input fields used (JSON string)
    generated_content = models.TextField(default='')    # LLM output (raw body text)

    # Generated file
    file = models.FileField(upload_to='generated_docs/%Y/%m/%d/')
    file_size = models.PositiveIntegerField(default=0)

    # Metadata
    model_used = models.CharField(max_length=100, default='')
    generation_time = models.FloatField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    # Security Lock & Passcode Protection
    is_locked = models.BooleanField(default=False)
    pin_hash = models.CharField(max_length=128, blank=True, default='')
    lock_hint = models.CharField(max_length=100, blank=True, default='')
    encrypt_export = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.document_type} v{self.version})"

    def format_size(self):
        bytes_val = self.file_size
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        else:
            return f"{bytes_val / (1024 * 1024):.1f} MB"

    def set_lock_pin(self, pin_code, hint='', encrypt_export=True):
        from django.contrib.auth.hashers import make_password
        self.is_locked = True
        self.pin_hash = make_password(pin_code)
        self.lock_hint = hint
        self.encrypt_export = encrypt_export
        self.save()

    def check_lock_pin(self, pin_code):
        from django.contrib.auth.hashers import check_password
        if not self.is_locked:
            return True
        return check_password(pin_code, self.pin_hash)

    def remove_lock(self):
        self.is_locked = False
        self.pin_hash = ''
        self.lock_hint = ''
        self.encrypt_export = False
        self.save()
