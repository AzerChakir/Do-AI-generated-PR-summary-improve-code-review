import { Routes } from '@angular/router';
import { Dashboard } from './dashboard/dashboard.component';
import { ReportDetail } from './report-detail/report-detail.component';

export const routes: Routes = [
  { path: '', component: Dashboard },
  { path: 'reports/:id', component: ReportDetail },
  { path: '**', redirectTo: '' },
];