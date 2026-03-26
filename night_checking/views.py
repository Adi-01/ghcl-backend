from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import TruckEntry, Transporter
from .serializers import TruckEntrySerializer
from rest_framework.pagination import PageNumberPagination
from .permissions import IsAdminUser,IsNightCheckingUser


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

class TruckEntryViewSet(viewsets.ModelViewSet):
    """
    GET /api/nightchecking/entries/ - List all truck entries.
    POST /api/nightchecking/entries/ - Create a new entry when a truck arrives.
    GET /api/nightchecking/entries/{entry_id}/ - Retrieve details of a specific truck.
    PATCH /api/nightchecking/entries/{entry_id}/ - Update fields (like changing paper_status to True).
    POST /api/nightchecking/entries/{entry_id}/mark_out/ - Your custom endpoint to instantly log the exit time.
    """
    queryset = TruckEntry.objects.all()
    serializer_class = TruckEntrySerializer
    permission_classes = [IsAdminUser|IsNightCheckingUser] 
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        # Order by newest first so pagination makes sense
        queryset = TruckEntry.objects.all().order_by('-entry_date') 
        
        # Filter by status if provided in the URL
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param.upper())
            
        return queryset

    def paginate_queryset(self, queryset):
        """
        Custom override: If the frontend is explicitly asking for 'IN' trucks,
        disable pagination entirely so they all show up on one screen.
        """
        if self.request.query_params.get('status') == 'IN':
            return None
        return super().paginate_queryset(queryset)
    

    @action(detail=True, methods=['post'])
    def mark_out(self, request, pk=None):
        """
        Shortcut endpoint to mark a truck as OUT.
        Records the current time and updates status.
        """
        truck_entry = self.get_object()
        
        if truck_entry.status == 'OUT':
            return Response(
                {"error": "This truck has already been marked OUT."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Allow manual exit_date from frontend, or default to right now
        manual_exit = request.data.get('exit_date')
        
        truck_entry.exit_date = manual_exit if manual_exit else timezone.now()
        truck_entry.status = 'OUT'
        truck_entry.save()

        serializer = self.get_serializer(truck_entry)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def transporters(self, request):
        """
        Returns a permanent list of unique transporter names.
        Even if all truck entries are deleted, these names remain.
        """
        # Fetch directly from our new permanent master list
        names = Transporter.objects.values_list('name', flat=True)
        
        return Response(list(names))
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        
        if not ids or not isinstance(ids, list):
            return Response({"detail": "Please provide a valid list of IDs."}, status=status.HTTP_400_BAD_REQUEST)
            
        deleted_count, _ = TruckEntry.objects.filter(entry_id__in=ids).delete()
        
        return Response({"detail": f"Successfully deleted {deleted_count} entries."}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], pagination_class=None, permission_classes=[IsAdminUser])
    def cleanup_preview(self, request):
        """Returns the absolute total count of records for a specific month string."""
        month_str = request.query_params.get('month_str') # e.g. "mar-2026"
        
        if not month_str:
            return Response({"error": "month_str is required."}, status=400)

        # Night Checking uses TruckEntry and entry_month
        count = TruckEntry.objects.filter(entry_month=month_str.lower()).count()
        
        return Response({
            "month": month_str.lower(),
            "count": count
        })

    @action(detail=False, methods=['post'], pagination_class=None, permission_classes=[IsAdminUser])
    def cleanup_execute(self, request):
        """Permanently deletes ALL records matching the month string."""
        month_str = request.data.get('month_str')
        
        if not month_str:
            return Response({"error": "month_str is required."}, status=400)

        # Night Checking uses TruckEntry and entry_month
        deleted_count, _ = TruckEntry.objects.filter(entry_month=month_str.lower()).delete()
        
        return Response({
            "message": f"Successfully deleted {deleted_count} records for {month_str}."
        }, status=status.HTTP_200_OK)