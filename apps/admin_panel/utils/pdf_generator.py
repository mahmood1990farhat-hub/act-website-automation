"""
PDF generation utility for complaints and lost property reports
"""
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.utils import timezone
from datetime import datetime


def generate_complaint_pdf(complaint):
    """
    Generate PDF for trip complaint
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=12,
        spaceBefore=12,
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    normal_style.leading = 14
    
    # Title
    elements.append(Paragraph("Complaint Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Complaint Details
    elements.append(Paragraph("Complaint Details", heading_style))
    
    complaint_data = [
        ['Complaint ID:', f"#{complaint.id}"],
        ['Ticket Number:', f"COMP-{complaint.id:06d}"],
        ['Date Submitted:', complaint.created_at.strftime('%B %d, %Y at %I:%M %p')],
        ['Status:', complaint.get_status_display()],
        ['Complaint Type:', complaint.get_complaint_type_display()],
    ]
    
    if complaint.resolved_at:
        complaint_data.append(['Resolved At:', complaint.resolved_at.strftime('%B %d, %Y at %I:%M %p')])
    
    complaint_table = Table(complaint_data, colWidths=[2*inch, 4*inch])
    complaint_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(complaint_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Complainant Information
    elements.append(Paragraph("Complainant Information", heading_style))
    complainant_data = [
        ['Name:', f"{complaint.user.first_name} {complaint.user.last_name}"],
        ['Email:', complaint.user.email],
        ['Phone:', complaint.user.phone_number or 'N/A'],
    ]
    
    complainant_table = Table(complainant_data, colWidths=[2*inch, 4*inch])
    complainant_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(complainant_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Trip Information
    if complaint.trip:
        elements.append(Paragraph("Trip Information", heading_style))
        trip = complaint.trip
        trip_data = [
            ['Trip ID:', f"#{trip.id}"],
            ['Trip Date:', trip.trip_date.strftime('%B %d, %Y') if trip.trip_date else 'N/A'],
            ['Trip Time:', trip.trip_time.strftime('%I:%M %p') if trip.trip_time else 'N/A'],
        ]
        
        if trip.pickup_str:
            trip_data.append(['Pickup Location:', trip.pickup_str])
        if trip.dropoff_str:
            trip_data.append(['Drop-off Location:', trip.dropoff_str])
        if trip.cost:
            trip_data.append(['Trip Cost:', f"£{trip.cost:.2f}"])
        
        trip_table = Table(trip_data, colWidths=[2*inch, 4*inch])
        trip_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(trip_table)
        elements.append(Spacer(1, 0.3*inch))
    
    # Complaint Description
    elements.append(Paragraph("Complaint Description", heading_style))
    elements.append(Paragraph(f"<b>Title:</b> {complaint.title}", normal_style))
    elements.append(Spacer(1, 0.1*inch))
    elements.append(Paragraph(f"<b>Description:</b><br/>{complaint.description}", normal_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Admin Response
    if complaint.admin_response:
        elements.append(Paragraph("Admin Response", heading_style))
        elements.append(Paragraph(complaint.admin_response, normal_style))
        elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    elements.append(Spacer(1, 0.5*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        f"Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}",
        footer_style
    ))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_lost_property_pdf(lost_property):
    """
    Generate PDF for lost property report
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=12,
        spaceBefore=12,
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    normal_style.leading = 14
    
    # Title
    elements.append(Paragraph("Lost Property Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Report Details
    elements.append(Paragraph("Report Details", heading_style))
    
    report_data = [
        ['Report ID:', f"#{lost_property.id}"],
        ['Ticket Number:', f"LOST-{lost_property.id:06d}"],
        ['Date Reported:', lost_property.created_at.strftime('%B %d, %Y at %I:%M %p')],
        ['Status:', lost_property.get_status_display()],
        ['Item Type:', lost_property.get_item_type_display()],
    ]
    
    if lost_property.found_at:
        report_data.append(['Found At:', lost_property.found_at.strftime('%B %d, %Y at %I:%M %p')])
    if lost_property.returned_at:
        report_data.append(['Returned At:', lost_property.returned_at.strftime('%B %d, %Y at %I:%M %p')])
    
    report_table = Table(report_data, colWidths=[2*inch, 4*inch])
    report_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(report_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Reporter Information
    elements.append(Paragraph("Reporter Information", heading_style))
    reporter_data = [
        ['Name:', f"{lost_property.user.first_name} {lost_property.user.last_name}"],
        ['Email:', lost_property.user.email],
        ['Phone:', lost_property.user.phone_number or 'N/A'],
        ['Contact Preference:', lost_property.get_contact_preference_display()],
    ]
    
    reporter_table = Table(reporter_data, colWidths=[2*inch, 4*inch])
    reporter_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(reporter_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Trip Information
    if lost_property.trip:
        elements.append(Paragraph("Trip Information", heading_style))
        trip = lost_property.trip
        trip_data = [
            ['Trip ID:', f"#{trip.id}"],
            ['Trip Date:', trip.trip_date.strftime('%B %d, %Y') if trip.trip_date else 'N/A'],
            ['Trip Time:', trip.trip_time.strftime('%I:%M %p') if trip.trip_time else 'N/A'],
        ]
        
        if trip.pickup_str:
            trip_data.append(['Pickup Location:', trip.pickup_str])
        if trip.dropoff_str:
            trip_data.append(['Drop-off Location:', trip.dropoff_str])
        
        trip_table = Table(trip_data, colWidths=[2*inch, 4*inch])
        trip_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(trip_table)
        elements.append(Spacer(1, 0.3*inch))
    
    # Item Details
    elements.append(Paragraph("Item Details", heading_style))
    item_data = [
        ['Item Description:', lost_property.item_description],
    ]
    
    if lost_property.item_color:
        item_data.append(['Color:', lost_property.item_color])
    if lost_property.item_brand:
        item_data.append(['Brand:', lost_property.item_brand])
    if lost_property.lost_location:
        item_data.append(['Lost Location:', lost_property.lost_location])
    
    item_table = Table(item_data, colWidths=[2*inch, 4*inch])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Admin Notes
    if lost_property.admin_notes:
        elements.append(Paragraph("Admin Notes", heading_style))
        elements.append(Paragraph(lost_property.admin_notes, normal_style))
        elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    elements.append(Spacer(1, 0.5*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        f"Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}",
        footer_style
    ))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

