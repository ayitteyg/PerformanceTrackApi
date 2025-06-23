from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        # Try to get related employee
        try:
            employee = user.employee_profile  # via related_name='member_profile'
            employee_id = employee.id
            employee_name = employee.name
            job = employee.job_description
        except:
            employee_id = None  # If no employee profile exists

        return Response({
            'token': token.key,
            'mid': employee_id,  # Return employee.id here instead of User.id
            'usid': user.id,
            'username': user.username,
            'employee_name':employee.name,
            'isCaptain': user.is_captain,
            'isManager': user.is_manager,
            'isSupervisor': user.is_supervisor,
            'isnoRole': user.is_noRole,
            'job':job
            
        })
