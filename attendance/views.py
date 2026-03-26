from rest_framework import viewsets, status
import calendar
from datetime import datetime
from django.db.models import Count,Q
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Attendance
from django.contrib.auth import get_user_model
from .serializers import (
    UserActiveShiftSerializer, 
    UserRecentAttendanceSerializer,
    AdminAttendanceLogSerializer
)
from rest_framework.pagination import PageNumberPagination
from .permissions import IsAdminUser

User = get_user_model()

# 1. Create a custom pagination class
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class AttendanceViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Attendance.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Returns the optimized state for the user frontend dashboard.
        """
        user = request.user
        active_shift = Attendance.objects.filter(user=user, check_out_time__isnull=True).first()
        
        recent_history = Attendance.objects.filter(
            user=user, 
            check_out_time__isnull=False
        ).order_by('-check_in_time')[:4]

        return Response({
            "is_active": active_shift is not None,
            "active_shift": UserActiveShiftSerializer(active_shift).data if active_shift else None,
            "recent_history": UserRecentAttendanceSerializer(recent_history, many=True).data
        }, status=status.HTTP_200_OK)


    @action(detail=False, methods=['post'])
    def punch(self, request):
        """
        Smart endpoint: Checks user in or out and returns the updated state.
        """
        user = request.user
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        now = timezone.now()

        active_shift = Attendance.objects.filter(user=user, check_out_time__isnull=True).first()

        if active_shift:
            # CHECK-OUT
            active_shift.check_out_time = now
            if latitude and longitude:
                active_shift.out_latitude = latitude
                active_shift.out_longitude = longitude
            active_shift.save()

            return Response({
                "message": "Checked out successfully",
                "status": "checked_out",
                # Return the completed shift data formatted for the history list
                "data": UserRecentAttendanceSerializer(active_shift).data 
            }, status=status.HTTP_200_OK)

        else:
            # CHECK-IN
            worklocation = request.data.get('worklocation')
            
            if not worklocation:
                return Response({"error": "worklocation is required for check-in."}, 
                                status=status.HTTP_400_BAD_REQUEST)

            local_time = timezone.localtime(now)
            att_date = local_time.strftime('%d-%b-%Y').lower() 
            att_month = local_time.strftime('%b-%Y').lower()   

            new_shift = Attendance.objects.create(
                user=user,
                worklocation=worklocation,
                attendance_date=att_date,
                attendance_month=att_month,
                in_latitude=latitude,
                in_longitude=longitude
            )

            return Response({
                "message": "Checked in successfully",
                "status": "checked_in",
                # Return the active shift data
                "data": UserActiveShiftSerializer(new_shift).data
            }, status=status.HTTP_201_CREATED)
        




class AdminAttendanceLogViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser] 
    serializer_class = AdminAttendanceLogSerializer
    lookup_field = 'attendance_id'
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Attendance.objects.select_related('user').all().order_by('-check_in_time')
        
        # Extract query parameters
        date_param = self.request.query_params.get('date', None)
        month_param = self.request.query_params.get('month', None)
        location_param = self.request.query_params.get('worklocation', None)

        if date_param:
            queryset = queryset.filter(attendance_date=date_param.lower())
            
        if month_param:
            queryset = queryset.filter(attendance_month=month_param.lower())
            
        if location_param:
            # Uses icontains for a flexible, case-insensitive search
            queryset = queryset.filter(worklocation__icontains=location_param) 
            
        return queryset

    def perform_update(self, serializer):
        """
        Intercept the save process. If the admin changed the check-in time, 
        we MUST recalculate the attendance_date/month strings to keep filters working.
        """
        instance = serializer.save()
        
        if 'check_in_time' in serializer.validated_data:
            local_time = timezone.localtime(instance.check_in_time)
            instance.attendance_date = local_time.strftime('%d-%b-%Y').lower()
            instance.attendance_month = local_time.strftime('%b-%Y').lower()
            instance.save(update_fields=['attendance_date', 'attendance_month'])


    @action(detail=False, methods=['get'])
    def register(self, request):
        month_param = request.query_params.get('month')
        location_param = request.query_params.get('worklocation')
        
        if not month_param:
            month_param = timezone.localtime().strftime('%b-%Y').lower()
        else:
            month_param = month_param.lower()
            
        try:
            month_obj = datetime.strptime(month_param, '%b-%Y')
            days_in_month = calendar.monthrange(month_obj.year, month_obj.month)[1]
        except ValueError:
            return Response({"error": "Invalid format"}, status=400)

        month_dates = [f"{str(day).zfill(2)}-{month_param}" for day in range(1, days_in_month + 1)]

        # --- 1. APPLY LOCATION FILTER TO ATTENDANCE RECORDS ---
        attendance_qs = Attendance.objects.filter(attendance_month=month_param)
        
        if location_param and location_param != "all":
            attendance_qs = attendance_qs.filter(worklocation__iexact=location_param)

        # --- UPDATE IS HERE ---
        # We annotate both the total count AND the active count
        attendance_data = attendance_qs \
            .values('user__user_id', 'attendance_date') \
            .annotate(
                present_count=Count('attendance_id'),
                active_count=Count('attendance_id', filter=Q(check_out_time__isnull=True))
            )

        matrix = {}
        for entry in attendance_data:
            u_id = str(entry['user__user_id']) 
            date_str = entry['attendance_date']
            count = entry['present_count']
            is_working = entry['active_count'] > 0 # True if they have ANY uncompleted shift today
            
            if u_id not in matrix:
                matrix[u_id] = {}
            
            # Store an object with both the count and the working status
            matrix[u_id][date_str] = {
                "count": count,
                "is_working": is_working
            }

        users = User.objects.filter(
            is_active=True, 
            labels__icontains="attend"
        ).order_by('username', 'email')

        register_list = []
        for user in users:
            user_id_str = str(user.user_id)
            user_name = user.username if user.username else user.email
            user_attendance = matrix.get(user_id_str, {})
            
            total_days_present = len(user_attendance.keys())
            # Safely sum the counts from our new dictionary structure
            total_shifts_worked = sum(day_data['count'] for day_data in user_attendance.values())

            # --- 2. CLEAN UP EMPTY ROWS ON FILTER ---
            if location_param and location_param != "all" and total_shifts_worked == 0:
                continue

            register_list.append({
                "user_id": user_id_str,
                "user_name": user_name,
                "attendance": user_attendance,       
                "total_days_present": total_days_present,
                "total_shifts_worked": total_shifts_worked
            })

        return Response({
            "month": month_param,
            "days_in_month": days_in_month,
            "dates": month_dates, 
            "register": register_list
        })
    
    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """
            Deletes multiple attendance records at once.
            Expects payload: { "attendance_ids": ["uuid-1", "uuid-2", ...] }
            """
        attendance_ids = request.data.get('attendance_ids', [])
            
        if not attendance_ids:
            return Response(
                    {"error": "No attendance IDs provided."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Filter by the provided IDs and delete them
        deleted_count, _ = Attendance.objects.filter(attendance_id__in=attendance_ids).delete()
            
        return Response(
                {"message": f"Successfully deleted {deleted_count} logs."}, 
                status=status.HTTP_200_OK
            )
    
    @action(detail=False, methods=['get'], pagination_class=None)
    def export(self, request):
        """
        Returns all filtered attendance records in a single, unpaginated JSON array.
        Perfect for frontend Excel generation.
        """
        # self.get_queryset() already contains all your custom filtering logic 
        # (date, month, worklocation), so we just reuse it!
        queryset = self.get_queryset()
        
        # Serialize the entire filtered queryset at once
        serializer = self.get_serializer(queryset, many=True)
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], pagination_class=None)
    def cleanup_preview(self, request):
        """Returns the absolute total count of records for a specific month string."""
        month_str = request.query_params.get('month_str') # e.g. "mar-2026"
        
        if not month_str:
            return Response({"error": "month_str is required."}, status=400)

        # FIX: Talk directly to the database to ignore accidental URL filters
        count = Attendance.objects.filter(attendance_month=month_str.lower()).count()
        
        return Response({
            "month": month_str.lower(),
            "count": count
        })

    @action(detail=False, methods=['post'], pagination_class=None)
    def cleanup_execute(self, request):
        """Permanently deletes ALL records matching the month string."""
        month_str = request.data.get('month_str')
        
        if not month_str:
            return Response({"error": "month_str is required."}, status=400)

        # FIX: Talk directly to the database to guarantee a complete wipe
        deleted_count, _ = Attendance.objects.filter(attendance_month=month_str.lower()).delete()
        
        return Response({
            "message": f"Successfully deleted {deleted_count} records for {month_str}."
        }, status=status.HTTP_200_OK)
