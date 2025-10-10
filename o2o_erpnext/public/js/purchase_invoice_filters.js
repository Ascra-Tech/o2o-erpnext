/**
 * Purchase Invoice Advanced Filter Utilities
 * Provides enhanced filter responsiveness and performance optimization
 */

frappe.provide('purchase_invoice_filters');

purchase_invoice_filters = {
    // Cache for filter performance
    filterCache: new Map(),
    lastFilterState: null,
    
    // Throttle utility for high-frequency events
    throttle: function(func, delay) {
        let timeoutId;
        let lastExecTime = 0;
        return function (...args) {
            const currentTime = Date.now();
            
            if (currentTime - lastExecTime > delay) {
                func.apply(this, args);
                lastExecTime = currentTime;
            } else {
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => {
                    func.apply(this, args);
                    lastExecTime = Date.now();
                }, delay - (currentTime - lastExecTime));
            }
        };
    },
    
    // Enhanced filter function with caching
    applyFiltersWithCache: function(filterConfig, rows) {
        const filterKey = JSON.stringify(filterConfig);
        
        // Check cache first
        if (this.filterCache.has(filterKey)) {
            return this.filterCache.get(filterKey);
        }
        
        const results = this.performFiltering(filterConfig, rows);
        
        // Cache results (limit cache size to prevent memory leaks)
        if (this.filterCache.size > 50) {
            const firstKey = this.filterCache.keys().next().value;
            this.filterCache.delete(firstKey);
        }
        
        this.filterCache.set(filterKey, results);
        return results;
    },
    
    // Core filtering logic
    performFiltering: function(config, rows) {
        const visibleRows = [];
        
        rows.each(function() {
            const $row = $(this);
            const rowData = {
                invoiceNumber: $row.data('invoice-number') || '',
                customer: $row.data('customer') || '',
                status: $row.data('status') || '',
                amount: parseFloat($row.data('amount')) || 0,
                fy: $row.data('fy') || '',
                isSelected: $row.find('.invoice-checkbox').is(':checked')
            };
            
            if (purchase_invoice_filters.shouldShowRow(rowData, config)) {
                visibleRows.push($row[0]);
            }
        });
        
        return visibleRows;
    },
    
    // Determine if row should be visible based on filters
    shouldShowRow: function(rowData, config) {
        // Quick filter check
        if (config.quickFilter !== 'all') {
            if (config.quickFilter === 'current-fy' && rowData.fy !== 'current') return false;
            if (config.quickFilter === 'last-fy' && rowData.fy !== 'last') return false;
        }
        
        // Status filter check
        if (config.statusFilter !== 'all') {
            if (!rowData.status.includes(config.statusFilter)) return false;
        }
        
        // Amount filter check
        if (config.amountFilter !== 'all') {
            switch(config.amountFilter) {
                case 'low':
                    if (rowData.amount >= 10000) return false;
                    break;
                case 'medium':
                    if (rowData.amount < 10000 || rowData.amount > 50000) return false;
                    break;
                case 'high':
                    if (rowData.amount <= 50000) return false;
                    break;
            }
        }
        
        // Search filter check
        if (config.searchValue) {
            const searchableText = (rowData.invoiceNumber + ' ' + rowData.customer).toLowerCase();
            if (!searchableText.includes(config.searchValue)) return false;
        }
        
        // Show selected only filter
        if (config.showSelectedOnly && !rowData.isSelected) return false;
        
        return true;
    },
    
    // Real-time filter update with visual feedback
    updateFiltersRealTime: function($wrapper, config) {
        const $rows = $wrapper.find('#invoices-tbody tr');
        
        // Show loading state
        this.showFilterLoading($wrapper, true);
        
        // Use requestAnimationFrame for smooth UI updates
        requestAnimationFrame(() => {
            const visibleRows = this.applyFiltersWithCache(config, $rows);
            
            // Batch DOM updates for better performance
            $rows.hide();
            $(visibleRows).show();
            
            // Update UI feedback
            this.updateFilterFeedback($wrapper, visibleRows.length, $rows.length);
            this.showFilterLoading($wrapper, false);
        });
    },
    
    // Show/hide loading indicator
    showFilterLoading: function($wrapper, show) {
        let $indicator = $wrapper.find('.filter-loading-indicator');
        
        if (show) {
            if ($indicator.length === 0) {
                $indicator = $('<div class="filter-loading-indicator" style="position: absolute; top: 0; right: 0; background: rgba(0,0,0,0.1); padding: 5px; border-radius: 3px; font-size: 11px;">⏳ Filtering...</div>');
                $wrapper.find('.filter-controls').css('position', 'relative').append($indicator);
            }
            $indicator.fadeIn(100);
        } else {
            $indicator.fadeOut(100);
        }
    },
    
    // Update filter feedback message
    updateFilterFeedback: function($wrapper, visibleCount, totalCount) {
        let $feedback = $wrapper.find('.filter-feedback');
        
        if ($feedback.length === 0) {
            $feedback = $('<div class="filter-feedback" style="font-size: 12px; color: #666; margin-top: 8px; padding: 5px; background: #f8f9fa; border-radius: 3px;"></div>');
            $wrapper.find('.filter-controls').append($feedback);
        }
        
        if (visibleCount === totalCount) {
            $feedback.html(`📊 Showing all <strong>${totalCount}</strong> invoices`);
        } else {
            $feedback.html(`🔍 Showing <strong>${visibleCount}</strong> of <strong>${totalCount}</strong> invoices`);
        }
        
        // Add quick clear filters option when filters are active
        if (visibleCount < totalCount) {
            if ($feedback.find('.clear-filters-btn').length === 0) {
                const $clearBtn = $('<button class="clear-filters-btn btn btn-xs btn-default" style="margin-left: 10px; font-size: 10px;">Clear All Filters</button>');
                $clearBtn.on('click', () => {
                    $wrapper.find('#quick-filter, #status-filter, #amount-filter').val('all');
                    $wrapper.find('#search-input').val('');
                    $wrapper.find('#filter-selected-btn').text('🔍 Show Selected Only').removeClass('btn-warning').addClass('btn-info');
                    // Trigger filter update
                    const resetConfig = {
                        quickFilter: 'all',
                        statusFilter: 'all', 
                        amountFilter: 'all',
                        searchValue: '',
                        showSelectedOnly: false
                    };
                    purchase_invoice_filters.updateFiltersRealTime($wrapper, resetConfig);
                });
                $feedback.append($clearBtn);
            }
        } else {
            $feedback.find('.clear-filters-btn').remove();
        }
    },
    
    // Clear filter cache (useful for performance)
    clearCache: function() {
        this.filterCache.clear();
    }
};

console.log("✅ Purchase Invoice Filters Utility Loaded");