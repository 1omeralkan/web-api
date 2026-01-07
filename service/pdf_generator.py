"""
PDF Report Generator
====================

Analiz sonuçlarını PDF formatında rapor olarak oluşturan servis.

ÖZELLİKLER:
-----------
- Performans özeti
- Güvenlik analizi detayları
- SSL sertifika bilgileri
- Optimizasyon önerileri
"""

import io
from datetime import datetime
from typing import Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from core.logging import get_logger

logger = get_logger(__name__)


def turkish_to_ascii(text: str) -> str:
    """
    Türkçe karakterleri ASCII karşılıklarına çevirir.
    PDF'te font problemi olmaması için.
    """
    turkish_map = {
        'ğ': 'g', 'Ğ': 'G',
        'ü': 'u', 'Ü': 'U',
        'ş': 's', 'Ş': 'S',
        'ı': 'i', 'İ': 'I',
        'ö': 'o', 'Ö': 'O',
        'ç': 'c', 'Ç': 'C',
    }
    for tr_char, ascii_char in turkish_map.items():
        text = text.replace(tr_char, ascii_char)
    return text


class PDFReportGenerator:
    """
    Analiz sonuçlarını PDF rapor olarak oluşturur.
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Özel stiller tanımlar."""
        # Başlık stili
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#6366f1'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Alt başlık stili
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.gray,
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        # Bölüm başlığı
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=20,
            spaceAfter=10
        ))
        
        # Grade stili
        self.styles.add(ParagraphStyle(
            name='Grade',
            parent=self.styles['Normal'],
            fontSize=48,
            textColor=colors.HexColor('#6366f1'),
            alignment=TA_CENTER
        ))
    
    def _tr(self, text: str) -> str:
        """Türkçe karakterleri ASCII'ye dönüştürür."""
        return turkish_to_ascii(str(text))
    
    def generate_report(self, data: Dict[str, Any]) -> bytes:
        """
        Analiz sonuçlarından PDF rapor oluşturur.
        
        Args:
            data: Analiz sonuç verileri
            
        Returns:
            bytes: PDF dosyası içeriği
        """
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        story = []
        
        # 1. Başlık
        story.append(Paragraph("Web API Performance Report", self.styles['CustomTitle']))
        story.append(Paragraph(
            f"Analiz Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            self.styles['CustomSubtitle']
        ))
        story.append(Spacer(1, 0.5*inch))
        
        # 2. URL Bilgisi
        url = data.get('url', 'N/A')
        story.append(Paragraph("Analiz Edilen URL", self.styles['SectionHeader']))
        story.append(Paragraph(f"<b>{url}</b>", self.styles['Normal']))
        story.append(Spacer(1, 0.25*inch))
        
        # 3. Grade Özeti
        story.append(Paragraph("Genel Degerlendirme", self.styles['SectionHeader']))
        
        performance = data.get('performance', {})
        security = data.get('security', {})
        
        perf_grade = performance.get('performance_grade', '-')
        sec_grade = security.get('headers', {}).get('grade', '-')
        
        grade_data = [
            ['Performans', 'Guvenlik'],
            [perf_grade, sec_grade]
        ]
        
        grade_table = Table(grade_data, colWidths=[3*inch, 3*inch])
        grade_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 36),
            ('TEXTCOLOR', (0, 1), (0, 1), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor('#10b981')),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, 1), 12),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ]))
        story.append(grade_table)
        story.append(Spacer(1, 0.3*inch))
        
        # 4. Performans Detayları
        story.append(Paragraph("Performans Detaylari", self.styles['SectionHeader']))
        
        perf_data = [
            ['Metrik', 'Deger'],
            ['Ortalama Response', f"{performance.get('avg_response_time_ms', 0):.0f} ms"],
            ['Min Response', f"{performance.get('min_response_time_ms', 0):.0f} ms"],
            ['Max Response', f"{performance.get('max_response_time_ms', 0):.0f} ms"],
            ['HTTP Status', str(performance.get('status_code', '-'))],
            ['Sayfa Boyutu', self._format_bytes(performance.get('content_length', 0))],
            ['HTTP Versiyon', performance.get('http_version', '-')],
            ['Basari Orani', f"%{performance.get('success_rate', 0)}"],
        ]
        
        perf_table = Table(perf_data, colWidths=[3*inch, 3*inch])
        perf_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(perf_table)
        story.append(Spacer(1, 0.3*inch))
        
        # 5. Timing Breakdown
        timing = performance.get('timing_breakdown', {})
        if timing:
            story.append(Paragraph("Timing Breakdown", self.styles['SectionHeader']))
            
            timing_data = [
                ['Asama', 'Sure'],
                ['DNS Lookup', f"{timing.get('dns_lookup_ms', 0):.1f} ms"],
                ['TCP Baglanti', f"{timing.get('tcp_connection_ms', 0):.1f} ms"],
                ['TLS Handshake', f"{timing.get('tls_handshake_ms', 0):.1f} ms"],
                ['TTFB', f"{timing.get('ttfb_ms', 0):.1f} ms"],
                ['Icerik Indirme', f"{timing.get('content_download_ms', 0):.1f} ms"],
            ]
            
            timing_table = Table(timing_data, colWidths=[3*inch, 3*inch])
            timing_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(timing_table)
            story.append(Spacer(1, 0.3*inch))
        
        # 6. Güvenlik Analizi
        story.append(Paragraph("Guvenlik Analizi", self.styles['SectionHeader']))
        
        headers_info = security.get('headers', {})
        sec_score = headers_info.get('score', 0)
        
        story.append(Paragraph(f"<b>Guvenlik Skoru:</b> {sec_score}/100", self.styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        
        headers_list = headers_info.get('headers', [])
        if headers_list:
            sec_data = [['Header', 'Durum', 'Oncelik']]
            for h in headers_list:
                status = 'Mevcut' if h.get('present') else 'Eksik'
                sec_data.append([
                    h.get('name', '-'),
                    status,
                    h.get('severity', '-').upper()
                ])
            
            sec_table = Table(sec_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
            sec_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(sec_table)
        story.append(Spacer(1, 0.3*inch))
        
        # 7. SSL Bilgileri
        ssl = data.get('ssl', {})
        if ssl and ssl.get('valid'):
            story.append(Paragraph("SSL Sertifika Bilgileri", self.styles['SectionHeader']))
            
            ssl_data = [
                ['Bilgi', 'Deger'],
                ['Subject', ssl.get('subject', '-')],
                ['Issuer', ssl.get('issuer', '-')],
                ['Son Gecerlilik', ssl.get('not_after', '-')[:10] if ssl.get('not_after') else '-'],
                ['Kalan Gun', str(ssl.get('days_remaining', '-'))],
                ['Protokol', ssl.get('protocol', '-')],
            ]
            
            ssl_table = Table(ssl_data, colWidths=[2*inch, 4*inch])
            ssl_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(ssl_table)
            story.append(Spacer(1, 0.3*inch))
        
        # 8. Öneriler
        suggestions = data.get('suggestions', [])
        if suggestions:
            story.append(Paragraph("Optimizasyon Onerileri", self.styles['SectionHeader']))
            
            for i, s in enumerate(suggestions, 1):
                title = self._tr(s.get('title', 'Oneri'))
                message = self._tr(s.get('message', ''))
                
                story.append(Paragraph(f"<b>{i}. {title}</b>", self.styles['Normal']))
                story.append(Paragraph(message, self.styles['Normal']))
                
                recommendations = s.get('recommendations', [])
                for rec in recommendations[:3]:  # Max 3 öneri
                    story.append(Paragraph(f"  - {self._tr(rec)}", self.styles['Normal']))
                
                story.append(Spacer(1, 0.1*inch))
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(
            "Bu rapor Web API Performance Analyzer tarafindan otomatik olusturulmustur.",
            ParagraphStyle('Footer', parent=self.styles['Normal'], fontSize=8, textColor=colors.gray, alignment=TA_CENTER)
        ))
        
        # PDF'i oluştur
        doc.build(story)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _format_bytes(self, bytes_val: int) -> str:
        """Byte değerini okunabilir formata çevirir."""
        if bytes_val == 0:
            return '0 B'
        k = 1024
        sizes = ['B', 'KB', 'MB', 'GB']
        i = 0
        while bytes_val >= k and i < len(sizes) - 1:
            bytes_val /= k
            i += 1
        return f"{bytes_val:.1f} {sizes[i]}"


# Singleton instance
pdf_generator = PDFReportGenerator()
