import uuid
import datetime

from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import transaction as dtransaction
from django.contrib.auth.models import User

# Create your models here.


class Product(models.Model):
    product_id = models.CharField(max_length=255, unique=True)
    stock_pcs = models.IntegerField(default=0)
    price = models.FloatField(default=0.0)
    shop_id = models.CharField(max_length=255, null=True, blank=True)
    vip = models.BooleanField(default=False, index=True)

    class Meta:
        db_table = 'shopper_product'


class Order(models.Model):

    SUCCESS = 1
    FAIL = 2
    PAYMENT_PENDING = 3
    NOT_IN_STOCK = 4
    CANCEL = 5

    ORDER_STATUS_OPTIONS = (
        (SUCCESS, 'Success'),
        (FAIL, 'Failed'),
        (PAYMENT_PENDING, 'Payment Pending'),
        (NOT_IN_STOCK, 'Not In Stock'),
        (CANCEL, 'Cancelled'),
    )

    order_id = models.CharField(max_length=255, null=True, blank=True,
                                unique=True)
    product = models.ForeignKey(Product, related_name='orders',
                                on_delete=models.CASCADE),
    qty = models.IntegerField(default=0)
    price = models.FloatField(default=0)

    # This filed is to make statistic routine more efficient
    total_price = models.FloatField(blank=True, null=True)

    shop_id = models.CharField(max_length=255, null=True, blank=True)

    # For search purpose in the future, we need a timestamp to record when the
    #  order created
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.IntegerField(default=PAYMENT_PENDING,
                                 choices=ORDER_STATUS_OPTIONS)

    def save(self, *args, **kwargs):
        self.total_price = self.qty * self.price
        super(Order, self).save(*args, **kwargs)

    class Meta:
        db_table = 'shopper_order'

    # For safety, we use custom order_id, not a serial number
    def __init__(self, *args, **kwargs):
        super(Order, self).__init__(*args, **kwargs)
        unique_id = str(uuid.uuid4().fields[0])[:7]
        datetime_now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        if not self.order_id:
            self.order_id = f'{datetime_now}{unique_id}'



class Customer(models.Model):
    user = models.OneToOneField(User, related_name='customer_user',
                                null=True, on_delete=models.SET_NULL)
    is_vip = models.BooleanField(default=False)


class Shop(models.Model):
    shop_id = models.CharField(max_length=255, unique=True)


@receiver(post_save, sender=Product)
def sync_order_status(sender, instance, created=False, *args, **kargs):

    # TODO: need use cache lock to prevent race condition

    if not created:
        # Always sync order status with the product
        if instance.stock_pcs > 0:
            stock_pcs = instance.stock_pcs
            with dtransaction.atomic():
                orders = instance.orders.filter(status=Order.NOT_IN_STOCK
                        ).order_by('qty')
                for order in orders:
                    if order.qty <= instance.stock_pcs:
                        order.status = Order.PAYMENT_PENDING
                        order.save()
                        stock_pcs -= order.qty
                        # TODO: to notify the customer in-stock, need use websocket
                    else:
                        break

                # Need to update new stock_pcs again?
                if stock_pcs != instance.stock_pcs:
                    Product.objects.filter(product_id=instance.product_id
                        ).update(stock_pcs=stock_pcs)
