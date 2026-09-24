from decimal import Decimal, ROUND_HALF_UP

def money(n): return float(Decimal(str(n)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
def net_realization(price, transport, storage, charges, quantity):
    costs = Decimal(str(transport))+Decimal(str(storage))+Decimal(str(charges))
    net = Decimal(str(price))-costs
    return {'net_per_quintal':money(net),'total_income':money(net*Decimal(str(quantity))), 'cost_per_quintal':money(costs),'gross_income':money(Decimal(str(price))*Decimal(str(quantity))), 'unit':'INR/quintal','basis':'user_entered'}

def rank(opportunities):
    rows=[dict(name=o.name,**net_realization(o.price,o.transport,o.storage,o.charges,o.quantity)) for o in opportunities]
    return sorted(rows,key=lambda x:x['net_per_quintal'],reverse=True)
