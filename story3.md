## As a visitor, I want to filter and sort search results by category, price range, and author so that I can narrow down my options to find the most relevant books

*ID:* EPIC-001-US-003  
*Epic:* EPIC-001

### Description
Advanced filtering and sorting capabilities empower users to refine their book discovery process based on specific criteria. This story enhances the search experience by allowing users to apply multiple filters simultaneously and sort results by different attributes, making it easier to find books that match their preferences and budget.

### Requirements
- Display filter panel on the left side of search results page with collapsible sections
- Implement category filter with checkboxes for all available book categories
- Provide price range filter with min/max input fields and predefined ranges (Under $10, $10-$20, $20-$50, Over $50)
- Include author filter with searchable dropdown showing authors from current results
- Add rating filter with star rating options (4+ stars, 3+ stars, etc.)
- Implement sort dropdown with options: Relevance, Price (Low to High), Price (High to Low), Newest First, Best Rated
- Show active filter count badge and 'Clear All Filters' button when filters are applied
- Update results dynamically within 1 second when filters or sort order changes

### Acceptance Criteria
- Given I am on the search results page, When I select one or more category filters, Then the results update to show only books in selected categories within 1 second
- Given I am viewing filtered results, When I enter a price range (min and max), Then the results show only books within that price range
- Given I have applied multiple filters, When I click 'Clear All Filters', Then all filters are removed and I see the original unfiltered results
- Given I am on the search results page, When I change the sort order dropdown, Then the results reorder according to the selected criteria immediately
- Given I have applied filters, When I see the filter count badge, Then it accurately reflects the number of active filters
- Given I apply filters that result in no matches, When the filter completes, Then I see a message 'No books match your filters' with a suggestion to adjust filter criteria

### Dependencies
Stories that must be completed first:
- EPIC-001-US-002