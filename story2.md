## As a visitor, I want to search for books by title, author, or keyword so that I can quickly find specific books I'm interested in

*ID:* EPIC-001-US-002  
*Epic:* EPIC-001

### Description
The search functionality enables visitors to actively find books rather than browsing through categories. This story implements a prominent search bar with autocomplete suggestions that helps users discover books efficiently, reducing the time from intent to finding desired books and improving overall user experience.

### Requirements
- Display search bar prominently in the header, visible on all pages
- Implement autocomplete that shows suggestions after user types 2+ characters
- Search across book titles, author names, and ISBN numbers
- Show up to 8 autocomplete suggestions with book cover thumbnail, title, and author
- Display 'No results found' message when search yields no matches
- Highlight matching text in autocomplete suggestions
- Return search results within 1 second for optimal user experience
- Preserve search query in the search bar after navigating to results page

### Acceptance Criteria
- Given I am on any page, When I type 2 or more characters in the search bar, Then I see up to 8 autocomplete suggestions within 1 second
- Given I see autocomplete suggestions, When I click on a suggestion, Then I am navigated to that book's detail page
- Given I have typed a search query, When I press Enter or click the search button, Then I am navigated to the search results page showing all matching books
- Given I search for a term with no matches, When the search completes, Then I see a 'No results found' message with suggestions to try different keywords
- Given I am viewing autocomplete suggestions, When I use arrow keys to navigate suggestions, Then the selected suggestion is highlighted and I can press Enter to select it
- Given I have performed a search, When I view the results page, Then my search query remains visible in the search bar for easy modification

### Dependencies
Stories that must be completed first:
- EPIC-001-US-001