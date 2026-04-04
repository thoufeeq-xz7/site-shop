def cart_context(request):
    cart = request.session.get('cart', {})
    total_items = sum(int(quantity) for quantity in cart.values())
    return {'cart_item_count': total_items}
