from django.shortcuts import render
from datetime import datetime, timedelta
from .model import strategy_analysis


def main_view(request):
    # querydict = request.GET.copy()
    # mylist = querydict.lists()
    
    cr = strategy_analysis.CalculateReturns()
    return_mean = cr.get_mean_returns()
    
    values = {"returns": return_mean}
    return render(request, 'strategy.html', values)