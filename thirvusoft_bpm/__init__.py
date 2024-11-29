
__version__ = '0.0.1'
from payments.templates.pages import razorpay_checkout
from thirvusoft_bpm.thirvusoft_bpm.code_backup.razorpay_checkout import gets_context

razorpay_checkout.get_context = gets_context