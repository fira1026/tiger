from functools import wraps
from rest_framework.response import Response

from shopper.models import Product
from mysite.libs import constants



def vip_required(function):
  @wraps(function)
  def wrap(request, *args, **kwargs):
        product_id = request.data.get('product_id')
        if product_id:
            product = Product.objects.filter(product_id=product_id).first()
            if product:
                if product.vip:
                    customer = request.user.customer_user
                    if customer.is_vip:
                        return function(request, *args, **kwargs)

        res = {constants.NOT_OK: 'vip check fail'}
        return Response(res, status=400)

  return wrap


def check_stock(function):
  @wraps(function)
  def wrap(request, *args, **kwargs):
        product_id = request.data.get('product_id')
        if product_id:
            product = Product.objects.filter(product_id=product_id).first()
            if product:
                order_qty = int(request.data.get('qty'))
                if order_qty <= product.stock_pcs:
                    return function(request, *args, **kwargs)

        res = {constants.NOT_OK: 'not in stock'}
        return Response(res, status=400)

  return wrap
