## As a first-time visitor, I want to see featured books and categories on the homepage so that I can quickly discover interesting books without searching

*ID:* EPIC-001-US-001  
*Epic:* EPIC-001

### Description
The homepage serves as the primary entry point for all visitors, showcasing the bookstore's offerings through curated collections and categories. This story establishes the foundation for user engagement by presenting featured books, bestsellers, and category navigation that helps visitors understand what the store offers and guides them toward their interests.

### Requirements
- Display hero section with 3-5 featured books rotating every 5 seconds
- Show 'Bestsellers' section with top 10 books based on sales data
- Display 'New Arrivals' section with latest 8 books added to catalog
- Present main book categories (Fiction, Non-Fiction, Children, Academic, etc.) with representative cover images
- Include promotional banner area for special offers or campaigns
- Show 'Recommended for You' section with 6 books (random for non-logged users, personalized for logged users)
- Ensure all book cards display: cover image, title, author, price, and rating
- Implement lazy loading for images to optimize page load time under 2 seconds

### Acceptance Criteria
- Given I am a visitor on the homepage, When the page loads, Then I see hero section with featured books, bestsellers section, new arrivals section, and category navigation within 2 seconds
- Given I am viewing the homepage, When I see a book card, Then it displays cover image, title, author name, current price, and average rating (if available)
- Given I am on the homepage, When I click on a book card, Then I am navigated to that book's detail page
- Given I am on the homepage, When I click on a category tile, Then I am navigated to the category page showing all books in that category
- Given the homepage has loaded, When I wait 5 seconds, Then the hero section automatically transitions to the next featured book
- Given I am a non-logged user, When I view 'Recommended for You' section, Then I see 6 randomly selected popular books from various categories