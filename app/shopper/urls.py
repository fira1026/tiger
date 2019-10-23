from django.urls import path

from shopper import views as shopper


urlpatterns = [
    path('product/', shopper.ProductViewSet.as_view(), name='product'),
    path('order/', shopper.OrderViewSet.as_view(), name='order'),
    path('top_3_products/', shopper.get_top_3_products, name='get_top_3_products'),
]
