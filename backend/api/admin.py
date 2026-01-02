from django.contrib import admin
from .models import Challenge, Result
from .models import GenerationRequest, GeneratedChallenge

admin.site.register(GenerationRequest)
admin.site.register(GeneratedChallenge)

admin.site.register(Challenge)
admin.site.register(Result)
