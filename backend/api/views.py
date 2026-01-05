from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
import logging
import fitz
import io
import base64

from .models import Document, ExtractedFundData
from .serializers import (
    MessageSerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentListSerializer,
    ExtractedFundDataSerializer
)
from .services import DocumentProcessingService

logger = logging.getLogger(__name__)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling document CRUD operations
    """
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return DocumentListSerializer
        elif self.action == 'create':
            return DocumentUploadSerializer
        return DocumentSerializer
    
    def list(self, request, *args, **kwargs):
        """List all documents with basic info"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        """
        Upload a new document and trigger processing
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Save document
        document = serializer.save()
        
        # Start async processing
        try:
            processing_service = DocumentProcessingService()
            processing_service.process_document(document.id)
            logger.info(f"Started processing for document {document.id}")
        except Exception as e:
            logger.error(f"Failed to start processing: {str(e)}")
            document.status = 'failed'
            document.error_message = f"Failed to start processing: {str(e)}"
            document.save()
        
        # Return response with document details
        response_serializer = DocumentSerializer(document, context={'request': request})
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request, *args, **kwargs):
        """Get detailed information about a specific document"""
        instance = self.get_object()
        serializer = DocumentSerializer(instance, context={'request': request})
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """Update document - supports updating extracted_data"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # If extracted_data was updated, sync with ExtractedFundData
        if 'extracted_data' in request.data:
            try:
                from .services import DocumentProcessingService
                # Re-sync the structured data
                extracted_data = instance.extracted_data
                
                # Helper to get value from structured or flat format
                def get_value(field_data):
                    if isinstance(field_data, dict) and 'value' in field_data:
                        return field_data['value']
                    return field_data
                
                # Update ExtractedFundData
                ExtractedFundData.objects.update_or_create(
                    document=instance,
                    defaults={
                        'fund_name': get_value(extracted_data.get('fund_name')),
                        'fund_code': get_value(extracted_data.get('fund_code')),
                        'management_company': get_value(extracted_data.get('management_company')),
                        'custodian_bank': get_value(extracted_data.get('custodian_bank')),
                        'management_fee': str(get_value(extracted_data.get('fees', {}).get('management_fee'))) if extracted_data.get('fees', {}).get('management_fee') else None,
                        'subscription_fee': str(get_value(extracted_data.get('fees', {}).get('subscription_fee'))) if extracted_data.get('fees', {}).get('subscription_fee') else None,
                        'redemption_fee': str(get_value(extracted_data.get('fees', {}).get('redemption_fee'))) if extracted_data.get('fees', {}).get('redemption_fee') else None,
                        'switching_fee': str(get_value(extracted_data.get('fees', {}).get('switching_fee'))) if extracted_data.get('fees', {}).get('switching_fee') else None,
                        'portfolio': extracted_data.get('portfolio', []),
                        'nav_history': extracted_data.get('nav_history', []),
                        'dividend_history': extracted_data.get('dividend_history', []),
                    }
                )
            except Exception as e:
                logger.error(f"Error syncing ExtractedFundData: {e}")
        
        return Response(serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        """Partial update (PATCH)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """
        Reprocess a document
        """
        document = self.get_object()
        
        # Check if document can be reprocessed
        if document.status == 'processing':
            return Response(
                {'error': 'Document is already being processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset status and trigger processing
        document.status = 'pending'
        document.error_message = None
        document.extracted_data = None
        document.save()
        
        # Start processing
        processing_service = DocumentProcessingService()
        processing_service.process_document(document.id)
        
        serializer = DocumentSerializer(document, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def optimized_pages(self, request, pk=None):
        """
        Get all pages from the optimized PDF as images (base64)
        """
        document = self.get_object()
        
        if not document.optimized_file:
            return Response(
                {'error': 'No optimized PDF available for this document'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            doc = fitz.open(document.optimized_file.path)
            pages = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Render page to image at 150 DPI for preview
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                
                # Convert to base64 for JSON transmission
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                
                pages.append({
                    'page_number': page_num + 1,
                    'image': f'data:image/png;base64,{img_base64}',
                    'width': pix.width,
                    'height': pix.height
                })
            
            doc.close()
            
            return Response({
                'total_pages': len(pages),
                'pages': pages
            })
            
        except Exception as e:
            logger.error(f"Error extracting optimized pages: {str(e)}")
            return Response(
                {'error': f'Failed to extract pages: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download the original PDF file
        """
        document = self.get_object()
        
        if not document.file:
            raise Http404("File not found")
        
        try:
            return FileResponse(
                document.file.open('rb'),
                as_attachment=True,
                filename=document.file_name
            )
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            raise Http404("File not found")
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get processing statistics
        """
        total = Document.objects.count()
        pending = Document.objects.filter(status='pending').count()
        processing = Document.objects.filter(status='processing').count()
        completed = Document.objects.filter(status='completed').count()
        failed = Document.objects.filter(status='failed').count()
        
        return Response({
            'total': total,
            'pending': pending,
            'processing': processing,
            'completed': completed,
            'failed': failed
        })


@api_view(['GET'])
def hello_world(request):
    """
    A simple API endpoint that returns a hello message
    """
    serializer = MessageSerializer(data={'message': 'Hello from Django!'})
    serializer.is_valid()
    return Response(serializer.data)


@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint
    """
    return Response({
        'status': 'healthy',
        'service': 'IDP Backend API'
    })

