from rest_framework import viewsets, status
from .models import JswSupplier, JswNagaurEntry
from .serializers import JswSupplierSerializer, JswNagaurEntrySerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .permissions import IsAdminUser, IsJswUser

class JswNagaurPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class JswSupplierViewSet(viewsets.ModelViewSet):
    queryset = JswSupplier.objects.all().order_by('name')
    serializer_class = JswSupplierSerializer
    permission_classes = [IsAdminUser|IsJswUser]

class JswNagaurEntryViewSet(viewsets.ModelViewSet):
    queryset = JswNagaurEntry.objects.all().order_by('-entry_date', '-serial_number')
    serializer_class = JswNagaurEntrySerializer
    permission_classes = [IsAdminUser|IsJswUser]
    lookup_field = 'entry_id'
    pagination_class = JswNagaurPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        
        date_param = self.request.query_params.get('date', None)
        month_param = self.request.query_params.get('month', None)

        if date_param:
            queryset = queryset.filter(entry_date=date_param)
            
        if month_param:
            queryset = queryset.filter(entry_month__iexact=month_param)

        return queryset
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        latest_entry = self.get_queryset().order_by('-serial_number').first()
        if latest_entry:
            serializer = self.get_serializer(latest_entry)
            return Response(serializer.data)
        return Response(None)

    # --- NEW: Secure Bulk Delete Action ---
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        
        if not ids or not isinstance(ids, list):
            return Response({"detail": "Please provide a valid list of IDs."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Delete the specific entries
        deleted_count, _ = JswNagaurEntry.objects.filter(entry_id__in=ids).delete()
        
        return Response({"detail": f"Successfully deleted {deleted_count} entries."}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], pagination_class=None)
    def export(self, request):
        """
        Returns all filtered attendance records in a single, unpaginated JSON array.
        Perfect for frontend Excel generation.
        """
        # self.get_queryset() already contains all your custom filtering logic 
        # (date, month), so we just reuse it!
        queryset = self.get_queryset()
        
        # Serialize the entire filtered queryset at once
        serializer = self.get_serializer(queryset, many=True)
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], pagination_class=None, permission_classes=[IsAdminUser])
    def cleanup_preview(self, request):
        """Returns the absolute total count of records for a specific month string."""
        month_str = request.query_params.get('month_str') # e.g. "mar-2026"
        
        if not month_str:
            return Response({"error": "month_str is required."}, status=400)

        # FIX: Targeting entry_month instead of attendance_month
        count = JswNagaurEntry.objects.filter(entry_month=month_str.lower()).count()
        
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

        # FIX: Targeting entry_month instead of attendance_month
        deleted_count, _ = JswNagaurEntry.objects.filter(entry_month=month_str.lower()).delete()
        
        return Response({
            "message": f"Successfully deleted {deleted_count} records for {month_str}."
        }, status=status.HTTP_200_OK)