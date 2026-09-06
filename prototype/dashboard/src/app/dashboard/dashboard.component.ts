import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ReportService } from '../services/report.service';
import { Health, ModelOption, ReportMeta, Report } from '../report.model';

export interface ParsedPr {
  owner: string;
  repo: string;
  pr: number;
}

export function parsePrAddress(input: string): ParsedPr | null {
  const value = input.trim();
  if (!value) {
    return null;
  }
  const githubUrl = /^(?:https?:\/\/)?(?:www\.)?github\.com\/([^/\s]+)\/([^/\s#]+)\/pull\/(\d+)\/?$/i;
  const shortForm = /^([^/\s#]+)\/([^/\s#]+)#(\d+)$/;
  let m = value.match(githubUrl);
  if (!m) {
    m = value.match(shortForm);
  }
  if (!m) {
    return null;
  }
  const pr = Number(m[3]);
  if (pr < 1) {
    return null;
  }
  return { owner: m[1], repo: m[2], pr };
}

@Component({
  selector: 'app-dashboard',
  imports: [FormsModule, RouterLink],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard {
  private readonly service = inject(ReportService);

  health = signal<Health | null>(null);
  reports = signal<ReportMeta[]>([]);
  loading = signal(false);
  analyzing = signal(false);
  error = signal('');
  success = signal('');

  prInput = signal('');
  advanced = signal(false);
  advancedOwner = signal('');
  advancedRepo = signal('');
  advancedPr = signal(1);
  mock = signal(false);

  models = signal<ModelOption[]>([]);
  model = signal('');
  deep = signal(true);
  requirements = signal('');

  parsed = computed<ParsedPr | null>(() => parsePrAddress(this.prInput()));
  parsedPr = computed<ParsedPr | null>(() => {
    if (this.advanced()) {
      const owner = this.advancedOwner().trim();
      const repo = this.advancedRepo().trim();
      const pr = Number(this.advancedPr());
      if (owner && repo && pr >= 1) {
        return { owner, repo, pr };
      }
      return null;
    }
    return this.parsed();
  });

  constructor() {
    this.refresh();
  }

  toggleAdvanced(): void {
    this.advanced.update((value) => !value);
    if (this.advanced()) {
      const parsed = this.parsed();
      if (parsed) {
        this.advancedOwner.set(parsed.owner);
        this.advancedRepo.set(parsed.repo);
        this.advancedPr.set(parsed.pr);
      }
    }
  }

  refresh(): void {
    this.loading.set(true);
    this.error.set('');
    this.service.health().subscribe({
      next: (health) => {
        this.health.set(health);
        if (health.models?.length) {
          this.models.set(health.models);
          this.model.set(
            health.models.some((m) => m.id === health.default_model)
              ? health.default_model
              : health.models[0].id,
          );
        }
        this.service.listReports().subscribe({
          next: (reports) => this.reports.set(reports),
          error: (err) => this.error.set(apiError(err)),
        });
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(apiError(err));
        this.loading.set(false);
      },
    });
  }

  analyze(): void {
    const parsed = this.parsedPr();
    if (!parsed) {
      this.error.set(
        'enter a pull request like owner/repo#123 or a full github.com URL (owner, repo and PR number are required)',
      );
      return;
    }
    this.analyzing.set(true);
    this.error.set('');
    this.success.set('');
    const effort = this.deep() ? 'deep' : 'standard';
    this.service
      .analyze(
        parsed.owner,
        parsed.repo,
        parsed.pr,
        this.mock(),
        this.mock() ? '' : this.model(),
        effort,
        this.requirements(),
      )
      .subscribe({
        next: (result: { report_id: string; report: Report }) => {
          this.analyzing.set(false);
          const mode = result.report.requested_mock
            ? ' (mock)'
            : ` (${result.report.model})`;
          this.success.set(
            `Analysis complete${mode} — verdict: ${result.report.verdict}`,
          );
          this.refresh();
        },
        error: (err) => {
          this.analyzing.set(false);
          this.error.set(apiError(err));
        },
      });
  }

  deleteReport(id: string): void {
    this.service.deleteReport(id).subscribe({
      next: () => this.refresh(),
      error: (err) => this.error.set(apiError(err)),
    });
  }

  formatDate(iso: string): string {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) {
      return iso;
    }
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}

function apiError(err: unknown): string {
  const e = err as { error?: { detail?: string }; status?: number; message?: string };
  return e?.error?.detail ?? e?.message ?? String(err);
}