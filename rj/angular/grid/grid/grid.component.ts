import {Component, ContentChild, EventEmitter, Input, OnDestroy, OnInit, Output, ViewChild} from '@angular/core';
import {MatPaginator} from '@angular/material';
import {select, Store} from '@ngrx/store';
import {Subject} from 'rxjs/Subject';
import {Subscription} from 'rxjs/Subscription';
import {merge} from 'rxjs/observable/merge';
import {combineLatest} from 'rxjs/observable/combineLatest';
import {filter} from 'rxjs/operators';
import {isNullOrUndefined, isUndefined} from 'util';
import {GridAction, GridColumnDef, GridRowClickEvent} from '../../../../store/grid/grid.model';
import {GridActionClickEvent} from '../../../../store/grid/grid.model';
import {GridSearchComponent} from '../grid-search/grid-search.component';
import {GridTableComponent} from '../grid-table/grid-table.component';
import * as fromGridIndex from '../../../../store/grid';
import * as fromGridActions from '../../../../store/grid/grid.actions';


@Component({
  selector: 'app-grid',
  templateUrl: './grid.component.html',
  styleUrls: ['./grid.component.scss']
})
export class GridComponent implements OnInit, OnDestroy {
  private _gridName = 'DEFAULT';
  @Input()
  set gridName(gridName: string) {
    this._gridName = (gridName && gridName.trim()) || 'DEFAULT';
  }

  get gridName() {
    return this._gridName;
  }

  @Input() noDataMessage: string;
  @Input() title: string;
  @Input() gridData: Array<any>;
  @Input() gridTotalElements: number;
  @Input() columns: GridColumnDef[] = [];
  @Input() gridActions: GridAction[] = [];
  @Input() pageActions: GridAction[] = [];
  @Input() set translatePrefix(translatePrefix) {
    console.warn('translatePrefix in app-grid is depricated');
  }
  @Input() advanced = true;
  @Output() rowClick: EventEmitter<GridRowClickEvent<any>> = new EventEmitter();
  @Output() actionClick: EventEmitter<GridActionClickEvent<any>> = new EventEmitter();
  @Output() filterChange = new EventEmitter();
  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(GridTableComponent) gridComponent: GridTableComponent;
  @ContentChild(GridSearchComponent) searchComponent: GridSearchComponent;
  private subscription: Subscription;
  private refresh$ = new Subject();

  constructor(private store: Store<fromGridIndex.GridState>) {
  }

  ngOnInit() {
    if (this.searchComponent) {
      this.searchComponent.gridName = this.gridName;
    }
    const gridState$ = this.store.pipe(
      select(fromGridIndex.selectGrid),
      select(this.gridName)
    );

    gridState$.pipe(
      filter(state => isUndefined(state))
    ).subscribe(() => this.store.dispatch(new fromGridActions.Reset({gridName: this.gridName})));

    this.subscription = merge(
      gridState$.pipe(filter(gridState => !isNullOrUndefined(gridState))),
      combineLatest(gridState$, this.refresh$, (state, refresh) => state),
    ).subscribe(state => this.filterChange.emit(state));
  }

  ngOnDestroy() {
    this.subscription.unsubscribe();
  }

  refresh() {
    this.refresh$.next();
  }

  toggleSearch() {
    this.searchComponent.toggleSearch();
    if (!this.gridComponent.hideFilters) {
      this.gridComponent.toggleFilters();
    }
  }

  toggleFilters() {
    this.gridComponent.toggleFilters();
    if (!this.searchComponent.hideSearch) {
      this.searchComponent.toggleSearch();
    }
  }

  forwardRowClick(event) {
    this.rowClick.emit(event);
  }

  forwardActionClick(event) {
    this.actionClick.emit(event);
  }

  emitActionClick(element, type) {
    this.actionClick.emit({
      element: element,
      type: type
    });
  }
}
