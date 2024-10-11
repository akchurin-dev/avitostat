from django.shortcuts import render
from django.views.generic import TemplateView


class PaymentView(TemplateView):
    template_name = 'payment.html'  # Путь к вашему шаблону payment.html

    def get(self, request, *args, **kwargs):
        user_id = request.user.id
        # Формируем контекст с ID пользователя
        context = {
            'current_user_id': user_id
        }
        # Рендерим шаблон с переданным контекстом
        return render(request, self.template_name, context)