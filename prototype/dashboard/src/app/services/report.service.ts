import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Health, ModelOption, Report, ReportMeta } from '../report.model';

@Injectable({ providedIn: 'root' })
export class ReportService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api';

  health(): Observable<Health> {
    return this.http.get<Health>(`${this.base}/health`);
  }

  models(): Observable<ModelOption[]> {
    return this.http.get<ModelOption[]>(`${this.base}/models`);
  }

  analyze(
    owner: string,
    repo: string,
    prNumber: number,
    mock: boolean,
    model: string,
    effort: string,
    requirements: string,
  ): Observable<{ report_id: string; analyzed_at_iso: string; report: Report }> {
    return this.http.post<{ report_id: string; analyzed_at_iso: string; report: Report }>(
      `${this.base}/analyze`,
      { owner, repo, pr_number: prNumber, mock, model, effort, requirements },
    );
  }

  listReports(): Observable<ReportMeta[]> {
    return this.http.get<ReportMeta[]>(`${this.base}/reports`);
  }

  getReport(reportId: string): Observable<Report> {
    return this.http.get<Report>(`${this.base}/reports/${encodeURIComponent(reportId)}`);
  }

  exportReport(reportId: string, format: 'html' | 'md' | 'pdf'): Observable<Blob> {
    return this.http.get(
      `${this.base}/reports/${encodeURIComponent(reportId)}/export?format=${format}`,
      { responseType: 'blob' },
    );
  }

  deleteReport(reportId: string): Observable<{ deleted: string }> {
    return this.http.delete<{ deleted: string }>(
      `${this.base}/reports/${encodeURIComponent(reportId)}`,
    );
  }
}