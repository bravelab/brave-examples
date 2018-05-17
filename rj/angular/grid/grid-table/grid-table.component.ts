import {
  AfterContentInit,
  AfterViewChecked,
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input, OnChanges, OnDestroy,
  OnInit,
  Output,
  ViewChild
} from '@angular/core';
import {MatPaginator, MatTableDataSource, PageEvent, Sort} from '@angular/material';
import {select, Store} from '@ngrx/store';
import {filter} from 'rxjs/operators';
import {has, get, find as _find} from 'lodash';
import {GridAction, GridActionClickEvent, GridColumnDef, GridNameState, GridRowClickEvent} from '../../../../store/grid/grid.model';
import * as fromGridIndex from '../../../../store/grid/index';
import * as fromGridActions from '../../../../store/grid/grid.actions';
import {TranslateService} from '@ngx-translate/core';
import {Subscription} from 'rxjs/Subscription';

@Component({
  selector: 'app-grid-table',
  templateUrl: './grid-table.component.html',
  styleUrls: ['./grid-table.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})

export class GridTableComponent implements AfterViewInit, OnInit, AfterViewChecked, OnDestroy {
  private defaultDataMessage = null;
  private dataMessage = null;
  @Input() gridName: string;
  @Input() gridData: any[];
  @Input() gridTotalElements: number;
  @Input() columns: GridColumnDef[] = [];
  @Input() gridActions: GridAction[] = [];
  @Input() advanced = true;

  @Input()
  set noDataMessage(message) {
    this.dataMessage = message;
  }

  get noDataMessage() {
    if (this.dataMessage) {
      return this.dataMessage;
    }
    return this.defaultDataMessage;
  }

  @Output() rowClick: EventEmitter<GridRowClickEvent<any>> = new EventEmitter();
  @Output() actionClick: EventEmitter<GridActionClickEvent<any>> = new EventEmitter();
  @ViewChild(MatPaginator) paginator: MatPaginator;
  hideFilters = false;
  itemsPerPagePagination = [5, 10, 20, 50, 100, 200];
  dataSource = new MatTableDataSource();
  columnWidth = 150;
  private columnGap = 10;
  private actionEmptyBoxWidth = 40;
  private cardPadding = 24;
  private tablePadding = 24;
  private subscriptions = new Subscription();

  constructor(private store: Store<fromGridIndex.GridState>, private cdRef: ChangeDetectorRef, private translate: TranslateService) {
  }

  ngOnInit() {
    const gridState$ = this.store.pipe(
      select(fromGridIndex.selectGrid),
      select(this.gridName)
    );
    this.subscriptions.add(
      gridState$.pipe(
        filter(state => has(state, 'pageIndex'))
      ).subscribe((state: GridNameState) => this.paginator.pageIndex = state.pageIndex)
    );
    this.subscriptions.add(
      gridState$.pipe(
        filter(state => has(state, 'pageSize'))
      ).subscribe((state: GridNameState) => this.paginator.pageSize = state.pageSize)
    );
    this.translate.get('grid.noDataMessage').subscribe((dataMessage) => {
      this.defaultDataMessage = dataMessage;
    });
  }

  ngAfterViewInit() {
    this.dataSource.data = this.gridData;
  }

  ngAfterViewChecked() {
    this.dataSource.data = this.gridData;
    this.cdRef.detectChanges();
  }

  ngOnDestroy() {
    this.subscriptions.unsubscribe();
  }

  getColumns() {
    const columnDefs = this.columns.map(def => def.columnDef);
    return this.gridActions.length > 0 ? [...columnDefs, 'gridActions'] : columnDefs;
  }

  onSort(sort: Sort) {
    this.store.dispatch(new fromGridActions.Sort({gridName: this.gridName, sort: sort}));
  }

  onPaginate(pagination: PageEvent) {
    this.store.dispatch(new fromGridActions.Paginate({gridName: this.gridName, pagination: pagination}));
  }

  emitRowClick(element, column) {
    this.rowClick.emit({
      element: element,
      column: column
    });
  }

  emitActionClick(element, name) {
    this.actionClick.emit({
      element: element,
      type: name
    });
  }

  toggleFilters() {
    this.hideFilters = !this.hideFilters;
  }

  calcMinWidth(): string {
    let gaps = this.columns.length - 1;

    let gridActionsWidth = 0;
    if (this.gridActions.length > 0) {
      gridActionsWidth = this.actionEmptyBoxWidth;
      gaps += 1;
    }

    const columnsWidth = this.columns.length * this.columnWidth;
    const totalPadding = 2 * (this.cardPadding + this.tablePadding);

    const gapsWidth = gaps * this.columnGap;
    return columnsWidth + gridActionsWidth + gapsWidth + totalPadding + 'px';
  }
}
