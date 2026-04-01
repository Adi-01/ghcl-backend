from rest_framework import viewsets, status
from .models import KajliTruckEntry, KajliAdjustment
from .serializers import KajliTruckEntrySerializer, KajliAdjustmentSerializer
from rest_framework.decorators import action
from django.db.models.functions import Coalesce
from django.db.models import Sum,IntegerField,F,Case,When
from rest_framework.response import Response
from .permissions import IsAdminUser,IsModerator

class KajliTruckEntryViewSet(viewsets.ModelViewSet):
    serializer_class = KajliTruckEntrySerializer
    permission_classes = [IsAdminUser | IsModerator]

    def get_queryset(self):
        queryset = KajliTruckEntry.objects.all().order_by('-entry_date')
        
        # Grab the date from the URL (e.g., ?date=2026-03-17)
        date_param = self.request.query_params.get('date', None)
        
        if date_param:
            # Filter strictly by the requested date
            queryset = queryset.filter(entry_date__date=date_param)
            
        return queryset
    
    @action(detail=False, methods=['get'])
    def godown_summary(self, request):
        allowed_godowns = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11]
        cargo_types = ['LSA', 'DSA', 'RBC']
        
        # 1. Get ALL truck sums in ONE query using conditional aggregation
        truck_data = KajliTruckEntry.objects.filter(
            godownnumber__in=allowed_godowns,
            cargo_type__in=cargo_types
        ).values('godownnumber', 'cargo_type').annotate(
            net_bags=Sum(
                Case(
                    When(loading_status='IN', then=F('bags')),
                    When(loading_status='OUT', then=-F('bags')),
                    default=0,
                    output_field=IntegerField()
                )
            )
        )

        # 2. Get ALL adjustments in ONE query 
        adj_data = KajliAdjustment.objects.filter(
            godownnumber__in=allowed_godowns,
            cargo_type__in=cargo_types
        ).values('godownnumber', 'cargo_type').annotate(
            total_adj=Sum('adjustment_value')
        )

        # Initialize the result map
        results = {g: {c: 0 for c in cargo_types} for g in allowed_godowns}

        # Merge Truck Data
        for item in truck_data:
            results[item['godownnumber']][item['cargo_type']] += item['net_bags'] or 0

        # Merge Adjustment Data
        for item in adj_data:
            results[item['godownnumber']][item['cargo_type']] += item['total_adj'] or 0

        # Format for frontend
        summary_data = [
            {
                'godown': g,
                'LSA': results[g]['LSA'],
                'DSA': results[g]['DSA'],
                'RBC': results[g]['RBC'],
            } for g in allowed_godowns
        ]

        return Response(summary_data)


    @action(detail=False, methods=['get'])
    def daily_godown_summary(self, request):
        date_param = self.request.query_params.get('date', None)
        
        # 1. Base Queryset for the selected date
        trucks_queryset = KajliTruckEntry.objects.all()
        if date_param:
            trucks_queryset = trucks_queryset.filter(entry_date__date=date_param)

        # 2. Identify ACTIVE Godowns (Only those with entries today)
        active_godowns = trucks_queryset.values_list('godownnumber', flat=True).distinct().order_by('godownnumber')

        # 3. Calculate Truck Stats
        stats = {
            "in_count": trucks_queryset.filter(truckstatus='IN - complete').count(),
            "out_count": trucks_queryset.filter(truckstatus='OUT - complete').count(),
        }

        # 4. Calculate Grid Data for IN and OUT separately
        summary_data = []
        for godown in active_godowns:
            def get_bags(cargo):
                qs = trucks_queryset.filter(godownnumber=godown, cargo_type=cargo)
                in_bags = qs.filter(loading_status='IN').aggregate(t=Coalesce(Sum('bags'), 0))['t']
                out_bags = qs.filter(loading_status='OUT').aggregate(t=Coalesce(Sum('bags'), 0))['t']
                return {"in": in_bags, "out": out_bags}

            # Calculate for this specific godown
            lsa = get_bags('LSA')
            dsa = get_bags('DSA')
            rbc = get_bags('RBC')

            # Only add to list if at least one cargo type has movement IN or OUT
            if any(val > 0 for cargo in [lsa, dsa, rbc] for val in cargo.values()):
                summary_data.append({
                    'godown': godown,
                    'LSA': lsa,
                    'DSA': dsa,
                    'RBC': rbc,
                })

        return Response({
            "stats": stats,
            "summary": summary_data
        })
    
    @action(detail=False, methods=['get'], pagination_class=None, permission_classes=[IsAdminUser])
    def cleanup_preview(self, request):
        """Returns the absolute total count of records for a specific month string."""
        month_str = request.query_params.get('month_str') # e.g. "mar-2026"
        
        if not month_str:
            return Response({"error": "month_str is required."}, status=400)

        # Night Checking uses TruckEntry and entry_month
        count = KajliTruckEntry.objects.filter(entry_month=month_str.lower()).count()
        
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

        # Night Checking uses KajliTruckEntry and entry_month
        deleted_count, _ = KajliTruckEntry.objects.filter(entry_month=month_str.lower()).delete()
        
        return Response({
            "message": f"Successfully deleted {deleted_count} records for {month_str}."
        }, status=status.HTTP_200_OK)
    


# Create a simple viewset for posting adjustments
class KajliAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = KajliAdjustment.objects.all()
    serializer_class = KajliAdjustmentSerializer
    permission_classes = [IsAdminUser | IsModerator]