from django.shortcuts import render, redirect, reverse
from . import forms, models
from django.db.models import Sum, Q
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from datetime import date
import io
from xhtml2pdf import pisa
from django.template.loader import get_template

# Helper functions to check user roles
def is_admin(user):
    # A user can be an admin if they have the ADMIN group or staff status
    return user.is_authenticated and (user.is_superuser or user.is_staff or user.groups.filter(name='ADMIN').exists())

def is_doctor(user):
    return user.groups.filter(name='DOCTOR').exists()

def is_patient(user):
    return user.groups.filter(name='PATIENT').exists()

# Helper function to render PDF
def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse("Rendering Error", status=400)


# Home view
def home_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request, 'hospital/index.html')


# Combined view for user role selection
def role_click_view(request, role):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    # Use a dynamic template path based on the role
    return render(request, f'hospital/{role}click.html')


# After login, redirect to the correct dashboard
@login_required
def afterlogin_view(request):
    if is_admin(request.user):
        return redirect('admin-dashboard')
    elif is_doctor(request.user):
        account_approved = models.Doctor.objects.filter(user_id=request.user.id, status=True).exists()
        if account_approved:
            return redirect('doctor-dashboard')
        else:
            return render(request, 'hospital/doctor_wait_for_approval.html')
    elif is_patient(request.user):
        account_approved = models.Patient.objects.filter(user_id=request.user.id, status=True).exists()
        if account_approved:
            return redirect('patient-dashboard')
        else:
            return render(request, 'hospital/patient_wait_for_approval.html')
    # Fallback for authenticated users without a role to prevent redirect loop
    return redirect('home')


# Signup views
def admin_signup_view(request):
    form = forms.AdminSigupForm()
    if request.method == 'POST':
        form = forms.AdminSigupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Correct password handling
            user.set_password(form.cleaned_data['password'])
            user.is_staff = True  # Set is_staff to true for admin users
            user.is_superuser = True # Set is_superuser for admin users
            user.save()
            my_admin_group, created = Group.objects.get_or_create(name='ADMIN')
            my_admin_group.user_set.add(user)
            return redirect('adminlogin')
    return render(request, 'hospital/adminsignup.html', {'form': form})


def doctor_signup_view(request):
    userForm = forms.DoctorUserForm()
    doctorForm = forms.DoctorForm()
    mydict = {'userForm': userForm, 'doctorForm': doctorForm}
    if request.method == 'POST':
        userForm = forms.DoctorUserForm(request.POST)
        doctorForm = forms.DoctorForm(request.POST, request.FILES)
        if userForm.is_valid() and doctorForm.is_valid():
            user = userForm.save(commit=False)
            user.set_password(userForm.cleaned_data['password'])
            user.save()
            doctor = doctorForm.save(commit=False)
            doctor.user = user
            doctor.save()
            my_doctor_group, created = Group.objects.get_or_create(name='DOCTOR')
            my_doctor_group.user_set.add(user)
            return redirect('doctorlogin')
    return render(request, 'hospital/doctorsignup.html', context=mydict)


def patient_signup_view(request):
    userForm = forms.PatientUserForm()
    patientForm = forms.PatientForm()
    mydict = {'userForm': userForm, 'patientForm': patientForm}
    if request.method == 'POST':
        userForm = forms.PatientUserForm(request.POST)
        patientForm = forms.PatientForm(request.POST, request.FILES)
        if userForm.is_valid() and patientForm.is_valid():
            user = userForm.save(commit=False)
            user.set_password(userForm.cleaned_data['password'])
            user.save()
            patient = patientForm.save(commit=False)
            patient.user = user
            patient.assignedDoctorId = request.POST.get('assignedDoctorId')
            patient.save()
            my_patient_group, created = Group.objects.get_or_create(name='PATIENT')
            my_patient_group.user_set.add(user)
            return redirect('patientlogin')
    return render(request, 'hospital/patientsignup.html', context=mydict)


# ADMIN RELATED VIEWS
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    doctors = models.Doctor.objects.all().order_by('-id')
    patients = models.Patient.objects.all().order_by('-id')
    
    doctor_counts = {'true': doctors.filter(status=True).count(), 'false': doctors.filter(status=False).count()}
    patient_counts = {'true': patients.filter(status=True).count(), 'false': patients.filter(status=False).count()}
    appointment_counts = {'true': models.Appointment.objects.filter(status=True).count(), 'false': models.Appointment.objects.filter(status=False).count()}
    
    mydict = {
        'doctors': doctors,
        'patients': patients,
        'doctorcount': doctor_counts['true'],
        'pendingdoctorcount': doctor_counts['false'],
        'patientcount': patient_counts['true'],
        'pendingpatientcount': patient_counts['false'],
        'appointmentcount': appointment_counts['true'],
        'pendingappointmentcount': appointment_counts['false'],
    }
    return render(request, 'hospital/admin_dashboard.html', context=mydict)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_doctor_view(request):
    return render(request, 'hospital/admin_doctor.html')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_doctor_view(request):
    doctors = models.Doctor.objects.filter(status=True)
    return render(request, 'hospital/admin_view_doctor.html', {'doctors': doctors})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def delete_doctor_from_hospital_view(request, pk):
    doctor = models.Doctor.objects.get(id=pk)
    user = models.User.objects.get(id=doctor.user_id)
    user.delete()
    doctor.delete()
    return redirect('admin-view-doctor')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def update_doctor_view(request, pk):
    doctor = models.Doctor.objects.get(id=pk)
    user = models.User.objects.get(id=doctor.user_id)
    userForm = forms.DoctorUserForm(instance=user)
    doctorForm = forms.DoctorForm(instance=doctor)
    mydict = {'userForm': userForm, 'doctorForm': doctorForm}
    if request.method == 'POST':
        userForm = forms.DoctorUserForm(request.POST, instance=user)
        doctorForm = forms.DoctorForm(request.POST, request.FILES, instance=doctor)
        if userForm.is_valid() and doctorForm.is_valid():
            user = userForm.save(commit=False)
            user.set_password(userForm.cleaned_data['password'])
            user.save()
            doctor = doctorForm.save(commit=False)
            doctor.status = True
            doctor.save()
            return redirect('admin-view-doctor')
    return render(request, 'hospital/admin_update_doctor.html', context=mydict)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_doctor_view(request):
    userForm = forms.DoctorUserForm()
    doctorForm = forms.DoctorForm()
    mydict = {'userForm': userForm, 'doctorForm': doctorForm}
    if request.method == 'POST':
        userForm = forms.DoctorUserForm(request.POST)
        doctorForm = forms.DoctorForm(request.POST, request.FILES)
        if userForm.is_valid() and doctorForm.is_valid():
            user = userForm.save(commit=False)
            user.set_password(userForm.cleaned_data['password'])
            user.save()
            doctor = doctorForm.save(commit=False)
            doctor.user = user
            doctor.status = True
            doctor.save()
            my_doctor_group, created = Group.objects.get_or_create(name='DOCTOR')
            my_doctor_group.user_set.add(user)
            return redirect('admin-view-doctor')
    return render(request, 'hospital/admin_add_doctor.html', context=mydict)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_approve_doctor_view(request):
    doctors = models.Doctor.objects.filter(status=False)
    return render(request, 'hospital/admin_approve_doctor.html', {'doctors': doctors})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def approve_doctor_view(request, pk):
    doctor = models.Doctor.objects.get(id=pk)
    doctor.status = True
    doctor.save()
    return redirect(reverse('admin-approve-doctor'))


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def reject_doctor_view(request, pk):
    doctor = models.Doctor.objects.get(id=pk)
    user = models.User.objects.get(id=doctor.user_id)
    user.delete()
    doctor.delete()
    return redirect('admin-approve-doctor')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_doctor_specialisation_view(request):
    doctors = models.Doctor.objects.filter(status=True)
    return render(request, 'hospital/admin_view_doctor_specialisation.html', {'doctors': doctors})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_patient_view(request):
    return render(request, 'hospital/admin_patient.html')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_patient_view(request):
    patients = models.Patient.objects.filter(status=True)
    return render(request, 'hospital/admin_view_patient.html', {'patients': patients})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def delete_patient_from_hospital_view(request, pk):
    patient = models.Patient.objects.get(id=pk)
    user = models.User.objects.get(id=patient.user_id)
    user.delete()
    patient.delete()
    return redirect('admin-view-patient')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def update_patient_view(request, pk):
    patient = models.Patient.objects.get(id=pk)
    user = models.User.objects.get(id=patient.user_id)
    userForm = forms.PatientUserForm(instance=user)
    patientForm = forms.PatientForm(instance=patient)
    mydict = {'userForm': userForm, 'patientForm': patientForm}
    if request.method == 'POST':
        userForm = forms.PatientUserForm(request.POST, instance=user)
        patientForm = forms.PatientForm(request.POST, request.FILES, instance=patient)
        if userForm.is_valid() and patientForm.is_valid():
            user = userForm.save(commit=False)
            user.set_password(userForm.cleaned_data['password'])
            user.save()
            patient = patientForm.save(commit=False)
            patient.status = True
            patient.assignedDoctorId = request.POST.get('assignedDoctorId')
            patient.save()
            return redirect('admin-view-patient')
    return render(request, 'hospital/admin_update_patient.html', context=mydict)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_patient_view(request):
    userForm = forms.PatientUserForm()
    patientForm = forms.PatientForm()
    mydict = {'userForm': userForm, 'patientForm': patientForm}
    if request.method == 'POST':
        userForm = forms.PatientUserForm(request.POST)
        patientForm = forms.PatientForm(request.POST, request.FILES)
        if userForm.is_valid() and patientForm.is_valid():
            user = userForm.save(commit=False)
            user.set_password(userForm.cleaned_data['password'])
            user.save()
            patient = patientForm.save(commit=False)
            patient.user = user
            patient.status = True
            patient.assignedDoctorId = request.POST.get('assignedDoctorId')
            patient.save()
            my_patient_group, created = Group.objects.get_or_create(name='PATIENT')
            my_patient_group.user_set.add(user)
            return redirect('admin-view-patient')
    return render(request, 'hospital/admin_add_patient.html', context=mydict)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_approve_patient_view(request):
    patients = models.Patient.objects.filter(status=False)
    return render(request, 'hospital/admin_approve_patient.html', {'patients': patients})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def approve_patient_view(request, pk):
    patient = models.Patient.objects.get(id=pk)
    patient.status = True
    patient.save()
    return redirect(reverse('admin-approve-patient'))


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def reject_patient_view(request, pk):
    patient = models.Patient.objects.get(id=pk)
    user = models.User.objects.get(id=patient.user_id)
    user.delete()
    patient.delete()
    return redirect('admin-approve-patient')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_discharge_patient_view(request):
    patients = models.Patient.objects.filter(status=True)
    return render(request, 'hospital/admin_discharge_patient.html', {'patients': patients})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def discharge_patient_view(request, pk):
    patient = models.Patient.objects.get(id=pk)
    days = (date.today() - patient.admitDate).days
    
    # Use select_related for a single, more efficient query
    assignedDoctor = models.User.objects.get(id=patient.assignedDoctorId)
    
    patientDict = {
        'patientId': pk,
        'name': patient.get_name,
        'mobile': patient.mobile,
        'address': patient.address,
        'symptoms': patient.symptoms,
        'admitDate': patient.admitDate,
        'todayDate': date.today(),
        'day': days,
        'assignedDoctorName': assignedDoctor.first_name,
    }

    if request.method == 'POST':
        try:
            roomCharge = int(request.POST['roomCharge']) * days
            doctorFee = int(request.POST['doctorFee'])
            medicineCost = int(request.POST['medicineCost'])
            otherCharge = int(request.POST['OtherCharge'])
            total = roomCharge + doctorFee + medicineCost + otherCharge

            feeDict = {
                'roomCharge': roomCharge,
                'doctorFee': doctorFee,
                'medicineCost': medicineCost,
                'OtherCharge': otherCharge,
                'total': total
            }
            patientDict.update(feeDict)

            pDD = models.PatientDischargeDetails(
                patientId=pk,
                patientName=patient.get_name,
                assignedDoctorName=assignedDoctor.first_name,
                address=patient.address,
                mobile=patient.mobile,
                symptoms=patient.symptoms,
                admitDate=patient.admitDate,
                releaseDate=date.today(),
                daySpent=days,
                medicineCost=medicineCost,
                roomCharge=roomCharge,
                doctorFee=doctorFee,
                OtherCharge=otherCharge,
                total=total
            )
            pDD.save()
            return render(request, 'hospital/patient_final_bill.html', context=patientDict)
        except (ValueError, KeyError):
            # Handle potential errors if POST data is missing or invalid
            # You might want to redirect to an error page or show a message
            return HttpResponse("Invalid form submission.", status=400)
            
    return render(request, 'hospital/patient_generate_bill.html', context=patientDict)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def download_pdf_view(request, pk):
    dischargeDetails = models.PatientDischargeDetails.objects.filter(patientId=pk).order_by('-id').first()
    
    if dischargeDetails:
        context = {
            'patientName': dischargeDetails.patientName,
            'assignedDoctorName': dischargeDetails.assignedDoctorName,
            'address': dischargeDetails.address,
            'mobile': dischargeDetails.mobile,
            'symptoms': dischargeDetails.symptoms,
            'admitDate': dischargeDetails.admitDate,
            'releaseDate': dischargeDetails.releaseDate,
            'daySpent': dischargeDetails.daySpent,
            'medicineCost': dischargeDetails.medicineCost,
            'roomCharge': dischargeDetails.roomCharge,
            'doctorFee': dischargeDetails.doctorFee,
            'OtherCharge': dischargeDetails.OtherCharge,
            'total': dischargeDetails.total,
        }
        return render_to_pdf('hospital/download_bill.html', context)
    else:
        return HttpResponse("No discharge details found for this patient.", status=404)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_appointment_view(request):
    return render(request, 'hospital/admin_appointment.html')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_appointment_view(request):
    appointments = models.Appointment.objects.filter(status=True)
    return render(request, 'hospital/admin_view_appointment.html', {'appointments': appointments})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_appointment_view(request):
    appointmentForm = forms.AppointmentForm()
    mydict = {'appointmentForm': appointmentForm}
    if request.method == 'POST':
        appointmentForm = forms.AppointmentForm(request.POST)
        if appointmentForm.is_valid():
            appointment = appointmentForm.save(commit=False)
            doctor = models.User.objects.get(id=request.POST.get('doctorId'))
            patient = models.User.objects.get(id=request.POST.get('patientId'))
            appointment.doctorId = doctor.id
            appointment.patientId = patient.id
            appointment.doctorName = doctor.first_name
            appointment.patientName = patient.first_name
            appointment.status = True
            appointment.save()
            return redirect('admin-view-appointment')
    return render(request, 'hospital/admin_add_appointment.html', context=mydict)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_approve_appointment_view(request):
    appointments = models.Appointment.objects.filter(status=False)
    return render(request, 'hospital/admin_approve_appointment.html', {'appointments': appointments})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def approve_appointment_view(request, pk):
    appointment = models.Appointment.objects.get(id=pk)
    appointment.status = True
    appointment.save()
    return redirect(reverse('admin-approve-appointment'))


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def reject_appointment_view(request, pk):
    appointment = models.Appointment.objects.get(id=pk)
    appointment.delete()
    return redirect('admin-approve-appointment')


# DOCTOR RELATED VIEWS
@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_dashboard_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    patient_count = models.Patient.objects.filter(status=True, assignedDoctorId=request.user.id).count()
    appointment_count = models.Appointment.objects.filter(status=True, doctorId=request.user.id).count()
    patient_discharged_count = models.PatientDischargeDetails.objects.filter(assignedDoctorName=request.user.first_name).count()
    
    appointments = models.Appointment.objects.filter(status=True, doctorId=request.user.id).select_related('patient').order_by('-id')
    
    mydict = {
        'patientcount': patient_count,
        'appointmentcount': appointment_count,
        'patientdischarged': patient_discharged_count,
        'appointments': appointments,
        'doctor': doctor,
    }
    return render(request, 'hospital/doctor_dashboard.html', context=mydict)


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_patient_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    return render(request, 'hospital/doctor_patient.html', {'doctor': doctor})


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_view_patient_view(request):
    patients = models.Patient.objects.filter(status=True, assignedDoctorId=request.user.id)
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    return render(request, 'hospital/doctor_view_patient.html', {'patients': patients, 'doctor': doctor})


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def search_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    query = request.GET.get('query', '')
    patients = models.Patient.objects.filter(
        status=True, 
        assignedDoctorId=request.user.id
    ).filter(
        Q(symptoms__icontains=query) | Q(user__first_name__icontains=query)
    )
    return render(request, 'hospital/doctor_view_patient.html', {'patients': patients, 'doctor': doctor})


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_view_discharge_patient_view(request):
    dischargedpatients = models.PatientDischargeDetails.objects.filter(assignedDoctorName=request.user.first_name).distinct()
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    return render(request, 'hospital/doctor_view_discharge_patient.html', {'dischargedpatients': dischargedpatients, 'doctor': doctor})


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_appointment_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    return render(request, 'hospital/doctor_appointment.html', {'doctor': doctor})


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_view_appointment_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    appointments = models.Appointment.objects.filter(status=True, doctorId=request.user.id).select_related('patient__user')
    return render(request, 'hospital/doctor_view_appointment.html', {'appointments': appointments, 'doctor': doctor})


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_delete_appointment_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    appointments = models.Appointment.objects.filter(status=True, doctorId=request.user.id).select_related('patient__user')
    return render(request, 'hospital/doctor_delete_appointment.html', {'appointments': appointments, 'doctor': doctor})


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def delete_appointment_view(request, pk):
    appointment = models.Appointment.objects.get(id=pk)
    appointment.delete()
    return redirect('doctor-delete-appointment')


# PATIENT RELATED VIEWS
@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_dashboard_view(request):
    patient = models.Patient.objects.get(user_id=request.user.id)
    # Use select_related for a single, more efficient query
    doctor = models.Doctor.objects.get(user_id=patient.assignedDoctorId)
    mydict = {
        'patient': patient,
        'doctorName': doctor.get_name,
        'doctorMobile': doctor.mobile,
        'doctorAddress': doctor.address,
        'symptoms': patient.symptoms,
        'doctorDepartment': doctor.department,
        'admitDate': patient.admitDate,
    }
    return render(request, 'hospital/patient_dashboard.html', context=mydict)


@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_appointment_view(request):
    patient = models.Patient.objects.get(user_id=request.user.id)
    return render(request, 'hospital/patient_appointment.html', {'patient': patient})


@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_book_appointment_view(request):
    appointmentForm = forms.PatientAppointmentForm()
    patient = models.Patient.objects.get(user_id=request.user.id)
    mydict = {'appointmentForm': appointmentForm, 'patient': patient, 'message': None}
    if request.method == 'POST':
        appointmentForm = forms.PatientAppointmentForm(request.POST)
        if appointmentForm.is_valid():
            appointment = appointmentForm.save(commit=False)
            appointment.doctorId = request.POST.get('doctorId')
            appointment.patientId = request.user.id
            appointment.doctorName = models.User.objects.get(id=request.POST.get('doctorId')).first_name
            appointment.patientName = request.user.first_name
            appointment.status = False
            appointment.save()
            return redirect('patient-view-appointment')
    return render(request, 'hospital/patient_book_appointment.html', context=mydict)


def patient_view_doctor_view(request):
    doctors = models.Doctor.objects.filter(status=True)
    patient = models.Patient.objects.get(user_id=request.user.id)
    return render(request, 'hospital/patient_view_doctor.html', {'patient': patient, 'doctors': doctors})


def search_doctor_view(request):
    patient = models.Patient.objects.get(user_id=request.user.id)
    query = request.GET.get('query', '')
    doctors = models.Doctor.objects.filter(status=True).filter(
        Q(department__icontains=query) | Q(user__first_name__icontains=query)
    )
    return render(request, 'hospital/patient_view_doctor.html', {'patient': patient, 'doctors': doctors})


@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_view_appointment_view(request):
    patient = models.Patient.objects.get(user_id=request.user.id)
    appointments = models.Appointment.objects.filter(patientId=request.user.id)
    return render(request, 'hospital/patient_view_appointment.html', {'appointments': appointments, 'patient': patient})


@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_discharge_view(request):
    patient = models.Patient.objects.get(user_id=request.user.id)
    dischargeDetails = models.PatientDischargeDetails.objects.filter(patientId=patient.id).order_by('-id').first()
    
    patientDict = {'is_discharged': False, 'patient': patient, 'patientId': request.user.id}
    
    if dischargeDetails:
        patientDict.update({
            'is_discharged': True,
            'patientName': dischargeDetails.patientName,
            'assignedDoctorName': dischargeDetails.assignedDoctorName,
            'address': patient.address,
            'mobile': patient.mobile,
            'symptoms': patient.symptoms,
            'admitDate': patient.admitDate,
            'releaseDate': dischargeDetails.releaseDate,
            'daySpent': dischargeDetails.daySpent,
            'medicineCost': dischargeDetails.medicineCost,
            'roomCharge': dischargeDetails.roomCharge,
            'doctorFee': dischargeDetails.doctorFee,
            'OtherCharge': dischargeDetails.OtherCharge,
            'total': dischargeDetails.total,
        })
    return render(request, 'hospital/patient_discharge.html', context=patientDict)


# ABOUT US AND CONTACT US VIEWS
def aboutus_view(request):
    return render(request, 'hospital/aboutus.html')


def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == 'POST':
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data['Email']
            name = sub.cleaned_data['Name']
            message = sub.cleaned_data['Message']
            # Your email sending logic goes here...
            # send_mail(subject, message, from_email, recipient_list)
            return render(request, 'hospital/contactus_success.html', {'name': name})
    return render(request, 'hospital/contactus.html', {'form': sub})