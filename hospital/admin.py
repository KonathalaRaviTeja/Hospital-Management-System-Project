from django.contrib import admin
from .models import Doctor, Patient, Appointment, PatientDischargeDetails, Feedback

# Doctor
class DoctorAdmin(admin.ModelAdmin):
    pass
admin.site.register(Doctor, DoctorAdmin)

# Patient
class PatientAdmin(admin.ModelAdmin):
    pass
admin.site.register(Patient, PatientAdmin)

# Appointment
class AppointmentAdmin(admin.ModelAdmin):
    pass
admin.site.register(Appointment, AppointmentAdmin)

# Patient Discharge
class PatientDischargeDetailsAdmin(admin.ModelAdmin):
    pass
admin.site.register(PatientDischargeDetails, PatientDischargeDetailsAdmin)

# Feedback
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')   # shows in admin list
    search_fields = ('name', 'email', 'message')     # searchable fields
admin.site.register(Feedback, FeedbackAdmin)
