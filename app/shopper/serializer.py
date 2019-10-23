from rest_framework import serializers
from django.db import transaction

from shopper.models import Product, Order


class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = '__all__'
        ref_name = 'product_serializers'


class OrderSerializer(serializers.ModelSerializer):

    product = ProductSerializer(required=False)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'
        ref_name = 'order_serializers'

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        request = self.context['request']
        if request.method == 'POST':  # create
            product_id = data['product_id']
            # ret['product_id'] = Product.objects.\
            #     filter(product_id=product_id).values_list('id', flat=True).get()
            ret['product'] = Product.objects.\
                filter(product_id=product_id).first()
        return ret

    def validate(self, data):
        '''
        # For patch, we only accept order to be canclled now, so simply set
        # order status to 'CANCELE'
        '''
        request = self.context['request']
        # For update, we only accept order to be canclled now, so simply set
        # order status to 'CANCEL'. Usually when the order is complete/success,
        # we should also update the order status. But since it is not part of
        # the interview task so I just ignore it.
        # 刪除訂單,庫存從0變回有值則提示商品到貨: this feature will be add to the
        # post_save() signal - sync_order_status() in models.py.
        if request.method == 'PATCH':
            data['status'] = Order.CANCEL
            return data

        elif request.method == 'PUT':
            # Usually we will provide customized error_code to ValidationError.
            # But I don't want to do it now.
            raise serializers.ValidationError(
                'Not support PUT method'
            )
        elif request.method == 'UPDATE':
            # TODO: validate each attribute
            pass

    @transaction.atomic
    def create(self, validated_data):
        product = validated_data['product']
        order_dict = {
            'product': product,
            'qty': int(validated_data['qty']),
            'price': product.price,
            'shop_id': product.shop_id
        }
        order = Order.objects.create(**order_dict)

        # Decrease Product.stock_pcs. Need lock object.
        product = Product.objects.select_for_update().get(pk=product.id)
        product.stock_pcs -= order.qty
        product.save()

        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        for key, val in validated_data.items():
            setattr(instance, key, validated_data[key])
        instance.save()

        # increase Product.stock_pcs. Need lock object
        product = Product.objects.select_for_update().get(pk=instance.id)
        product.stock_pcs += instance.qty
        product.save()

        return instance
