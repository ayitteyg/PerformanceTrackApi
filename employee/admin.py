
# Register your models here.
# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import( Employee, PumpTarget, CustomUser, Captain, ShopTarget, FuelSales, ShopSales,
                    WeeklyEvaluation, AttendanceRegister, AttendantEvaluation)
from import_export.admin import ImportExportModelAdmin


@admin.register(Employee)
class EmployeeAdmin(ImportExportModelAdmin):
    list_display = ('name', 'job_description', 'status', 'site')
    list_filter = ('status', 'job_description', 'site')
    search_fields = ('name', 'contact')
    fieldsets = (
        (None, {
            'fields': ('user', 'name', 'gender', 'contact')
        }),
        ('Employment Details', {
            'fields': ('job_description', 'date_employed', 'site', 'status')
        }),
        ('Training Info', {
            'fields': ('training_start', 'training_end'),
            'classes': ('collapse',)
        }),
        ('Guarantor Info', {
            'fields': ('guarantor_name', 'guarantor_contact'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PumpTarget)
class PumpTargetAdmin(admin.ModelAdmin):
    pass


@admin.register(ShopTarget)
class ShopTargetAdmin(admin.ModelAdmin):
    pass

@admin.register(FuelSales)
class FuelSalesAdmin(ImportExportModelAdmin):
    pass


@admin.register(ShopSales)
class ShopSalesAdmin(ImportExportModelAdmin):
    pass


@admin.register(WeeklyEvaluation)
class WeeklyEvaluationAdmin(ImportExportModelAdmin):
    pass


@admin.register(AttendanceRegister)
class AttendanceRegisterAdmin(ImportExportModelAdmin):
    pass



@admin.register(AttendantEvaluation)
class AttendantEvaluationAdmin(ImportExportModelAdmin):
    pass

@admin.register(Captain)
class CaptainAdmin(admin.ModelAdmin):
    pass


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'is_manager', 'is_supervisor', 'is_noRole', 'is_captain', 'is_staff']

    # Add other roles to the regular (edit) form
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('is_manager', 'is_supervisor', 'is_noRole', 'is_captain')}),
    )

    # Add other roles to the add user form
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('is_manager', 'is_supervisor', 'is_noRole', 'is_captain')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)