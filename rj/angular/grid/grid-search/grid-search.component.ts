import {Component, Input, OnInit, ViewChild} from '@angular/core';
import {FormGroup, FormGroupDirective} from '@angular/forms';
import {Store} from '@ngrx/store';
import * as fromGridIndex from '../../../../store/grid';
import * as fromGridActions from '../../../../store/grid/grid.actions';

@Component({
  selector: 'app-grid-search',
  templateUrl: './grid-search.component.html',
  styleUrls: ['./grid-search.component.scss'],
})
export class GridSearchComponent implements OnInit {
  @Input() formGroup: FormGroup;
  @ViewChild(FormGroupDirective) filterForm: FormGroupDirective;
  gridName: string;
  hideSearch = true;

  constructor(private store: Store<fromGridIndex.GridState>) {
  }

  ngOnInit() {
    this.filterForm.ngSubmit.subscribe(() => {
      this.store.dispatch(new fromGridActions.Search({gridName: this.gridName, search: this.filterForm.value}));
      this.hideSearch = true;
    });
  }

  toggleSearch() {
    this.hideSearch = !this.hideSearch;
  }
}
