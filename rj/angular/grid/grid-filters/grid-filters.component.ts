import {Component, Input} from '@angular/core';
import {Store} from '@ngrx/store';
import * as fromGridIndex from '../../../../store/grid';
import * as fromGridActions from '../../../../store/grid/grid.actions';
import {indexOf} from 'lodash';
import {GridColumnDef} from '../../../../store/grid/grid.model';

@Component({
  selector: 'app-grid-filters',
  templateUrl: './grid-filters.component.html',
  styleUrls: ['./grid-filters.component.scss']
})
export class GridFiltersComponent {
  @Input() gridName: string;
  @Input() columns: GridColumnDef[];
  @Input() addBox: boolean;
  @Input() delay = 1000;
  @Input() columnWidth: number;

  constructor(private store: Store<fromGridIndex.GridState>) { }

  onFilter(filter) {
    this.store.dispatch(new fromGridActions.Filter({gridName: this.gridName, filter: filter}));
  }

}
