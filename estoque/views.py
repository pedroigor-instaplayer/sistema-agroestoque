from django.http import HttpResponse


def inicio(request):
    return HttpResponse("Sistema AgroEstoque - Da Roça Inteligente")
