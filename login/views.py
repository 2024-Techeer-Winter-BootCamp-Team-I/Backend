from django.shortcuts import render,redirect
# Create your views here.

def login(request):
    return render(request, 'login/index.html')

def home(request):
    return render(request,'login/home.html')
