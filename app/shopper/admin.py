from django.contrib import admin

from shopper.models import Product, Order, Customer
# Register your models here.


class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_id', 'stock_pcs', 'price', 'shop_id', 'vip']
    readonly_fields = ['product_id']
    ordering = ['product_id', 'shop_id']


class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'product__product_id', 'qty', 'price',
                    'total_price', 'shop_id', 'created_at', 'status']
    readonly_fields = ['order_id']
    ordering = ['created_at']


class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_id, is_vip']


admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Customer, CustomerAdmin)
