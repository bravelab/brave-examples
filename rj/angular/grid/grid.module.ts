import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import {StoreModule} from '@ngrx/store';
import {SharedModule} from '../../shared.module';
import {GridComponent} from './grid/grid.component';
import {GridSearchComponent} from './grid-search/grid-search.component';
import { GridTableComponent } from './grid-table/grid-table.component';
import * as fromGridReducer from '../../../store/grid/grid.reducer';
import { GridFiltersComponent } from './grid-filters/grid-filters.component';
import {TranslateModule} from '@ngx-translate/core';


@NgModule({
  imports: [
    CommonModule,
    SharedModule,
    TranslateModule,
    StoreModule.forFeature('Grid', fromGridReducer.reducer)
  ],
  declarations: [
    GridComponent,
    GridSearchComponent,
    GridTableComponent,
    GridFiltersComponent
  ],
  exports: [
    GridComponent,
    GridSearchComponent
  ],
})
export class GridModule { }
