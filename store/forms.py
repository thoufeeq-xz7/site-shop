from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Product


INPUT_CLASS = (
    'w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 '
    'outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-200'
)
TEXTAREA_CLASS = INPUT_CLASS + ' min-h-[140px] resize-y'


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'you@example.com'}))
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'First name'}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Last name'}),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': INPUT_CLASS, 'placeholder': 'Choose a username'})
        self.fields['password1'].widget.attrs.update({'class': INPUT_CLASS, 'placeholder': 'Create a password'})
        self.fields['password2'].widget.attrs.update({'class': INPUT_CLASS, 'placeholder': 'Confirm your password'})

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        return user


class StyledAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Password'}))


class ProductForm(forms.ModelForm):
    gallery_image_1 = forms.URLField(
        required=False,
        widget=forms.URLInput(
            attrs={'class': INPUT_CLASS, 'placeholder': 'https://example.com/product-photo-1.jpg'}
        ),
    )
    gallery_image_2 = forms.URLField(
        required=False,
        widget=forms.URLInput(
            attrs={'class': INPUT_CLASS, 'placeholder': 'https://example.com/product-photo-2.jpg'}
        ),
    )
    gallery_image_3 = forms.URLField(
        required=False,
        widget=forms.URLInput(
            attrs={'class': INPUT_CLASS, 'placeholder': 'https://example.com/product-photo-3.jpg'}
        ),
    )

    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Minimalist Cotton Tee'}),
            'description': forms.Textarea(attrs={'class': TEXTAREA_CLASS, 'placeholder': 'Write a compelling product story...'}),
            'price': forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': '1499', 'step': '0.01'}),
            'category': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Apparel'}),
            'image': forms.URLInput(attrs={'class': INPUT_CLASS, 'placeholder': 'https://example.com/cover-photo.jpg'}),
        }

    def clean_price(self):
        price = self.cleaned_data['price']
        if price <= 0:
            raise forms.ValidationError('Price must be greater than zero.')
        return price

    def get_gallery_image_urls(self):
        return [
            self.cleaned_data[field_name].strip()
            for field_name in ['gallery_image_1', 'gallery_image_2', 'gallery_image_3']
            if self.cleaned_data.get(field_name)
        ]


class CheckoutForm(forms.Form):
    include_customer_details = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-slate-900 focus:ring-slate-500'}),
        label='Include my contact details in the WhatsApp message'
    )
    customer_name = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Your full name'}),
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': '+91 98765 43210'}),
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': TEXTAREA_CLASS, 'placeholder': 'Delivery address'}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': TEXTAREA_CLASS, 'placeholder': 'Notes, landmark, preferred contact time...'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        include_details = cleaned_data.get('include_customer_details', False)

        if include_details:
            # Make fields required when checkbox is checked
            required_fields = ['customer_name', 'phone_number', 'address']
            for field_name in required_fields:
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, f'{field_name.replace("_", " ").title()} is required when including customer details.')

        return cleaned_data

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '')
        if phone:
            phone = ''.join(char for char in phone if char.isdigit() or char == '+')
            if len(phone.replace('+', '')) < 10:
                raise forms.ValidationError('Please enter a valid phone number.')
        return phone


class ContactForm(forms.Form):
    name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Your name'}))
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'you@example.com'}),
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': '+91 98765 43210'}),
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': TEXTAREA_CLASS, 'placeholder': 'How can we help?'}),
    )
