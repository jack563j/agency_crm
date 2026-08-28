"""URL routing for sales app."""
from django.urls import path
from . import views

urlpatterns = [
    path("quotes/", views.quote_list_view, name="quote_list"),
    path("quotes/add/", views.quote_create_view, name="quote_create"),
    path("quotes/<int:pk>/convert/", views.quote_convert_view, name="quote_convert"),

    path("orders/", views.order_list_view, name="order_list"),
    path("orders/<int:pk>/invoice/", views.order_invoice_view, name="order_invoice"),

    path("products/", views.product_list_view, name="product_list"),
]
