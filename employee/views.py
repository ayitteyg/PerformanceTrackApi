from django.shortcuts import render, redirect
from django.views import generic, View
from django.views.generic import TemplateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth import authenticate, login
from . models import FuelSales
from . functions import print_model_objects, reset_model_data, convert_to_json, read_file




