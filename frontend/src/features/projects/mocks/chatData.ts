import type { Message, Conversation, AgentType } from '../types/chat'

// Mock chat conversations with different agents
export const MOCK_CONVERSATIONS: Record<AgentType | 'ALL', Message[]> = {
  ALL: [
    {
      id: '1',
      role: 'user',
      content: 'How is the project progressing?',
      timestamp: new Date('2025-01-14T09:00:00'),
    },
    {
      id: '2',
      role: 'agent',
      content:
        'The project is on track. We have 12 stories in progress, 8 in review, and 15 completed. The current sprint velocity is looking good.',
      agentType: 'FLOW_MANAGER',
      timestamp: new Date('2025-01-14T09:01:00'),
    },
    {
      id: '3',
      role: 'user',
      content: 'What are the main blockers right now?',
      timestamp: new Date('2025-01-14T09:05:00'),
    },
    {
      id: '4',
      role: 'agent',
      content:
        'We have 2 blocked stories: one waiting for API documentation and another requiring database schema approval. I recommend prioritizing these to unblock the team.',
      agentType: 'FLOW_MANAGER',
      timestamp: new Date('2025-01-14T09:05:30'),
    },
  ],

  FLOW_MANAGER: [
    {
      id: 'fm1',
      role: 'user',
      content: 'Can you help me prioritize the backlog?',
      timestamp: new Date('2025-01-14T10:00:00'),
    },
    {
      id: 'fm2',
      role: 'agent',
      content:
        'Based on business value and dependencies, I suggest prioritizing:\n\n1. User authentication system (HIGH priority, blocks other features)\n2. Product catalog API (HIGH priority, needed by frontend team)\n3. Payment integration (MEDIUM priority)\n\nWould you like me to update the story priorities accordingly?',
      agentType: 'FLOW_MANAGER',
      timestamp: new Date('2025-01-14T10:01:00'),
    },
    {
      id: 'fm3',
      role: 'user',
      content: 'Yes, please update them',
      timestamp: new Date('2025-01-14T10:02:00'),
    },
    {
      id: 'fm4',
      role: 'agent',
      content:
        '✅ Priorities updated successfully! I\'ve also moved the authentication story to "In Progress" column and assigned it to the Developer agent.',
      agentType: 'FLOW_MANAGER',
      timestamp: new Date('2025-01-14T10:02:30'),
    },
  ],

  BUSINESS_ANALYST: [
    {
      id: 'ba1',
      role: 'user',
      content: 'I need to create user stories for the checkout feature',
      timestamp: new Date('2025-01-14T11:00:00'),
    },
    {
      id: 'ba2',
      role: 'agent',
      content:
        'I can help you create comprehensive user stories for the checkout feature. Here\'s what I propose:\n\n**Epic**: Checkout Flow\n\n**User Stories**:\n1. As a customer, I want to review my cart items before checkout\n2. As a customer, I want to enter shipping information\n3. As a customer, I want to select payment method\n4. As a customer, I want to see order confirmation\n\nShould I create these stories with acceptance criteria?',
      agentType: 'BUSINESS_ANALYST',
      timestamp: new Date('2025-01-14T11:01:00'),
    },
    {
      id: 'ba3',
      role: 'user',
      content: 'Yes, please include acceptance criteria',
      timestamp: new Date('2025-01-14T11:02:00'),
    },
    {
      id: 'ba4',
      role: 'agent',
      content:
        '✅ Created 4 user stories with detailed acceptance criteria and added them to the "Checkout Flow" epic. Each story includes:\n- User story format\n- Acceptance criteria\n- Business value estimate\n- Dependencies\n\nYou can find them in the TODO column.',
      agentType: 'BUSINESS_ANALYST',
      timestamp: new Date('2025-01-14T11:03:00'),
    },
  ],

  DEVELOPER: [
    {
      id: 'dev1',
      role: 'user',
      content: 'What technologies should we use for the authentication system?',
      timestamp: new Date('2025-01-14T12:00:00'),
    },
    {
      id: 'dev2',
      role: 'agent',
      content:
        'For the authentication system, I recommend:\n\n**Backend**:\n- JWT tokens for stateless authentication\n- bcrypt for password hashing\n- Redis for session management\n\n**Frontend**:\n- React Context for auth state\n- Axios interceptors for token refresh\n- Protected route components\n\n**Security**:\n- HTTPS only\n- CSRF protection\n- Rate limiting on login attempts\n\nWould you like me to create technical tasks for implementing this?',
      agentType: 'DEVELOPER',
      timestamp: new Date('2025-01-14T12:01:00'),
    },
    {
      id: 'dev3',
      role: 'user',
      content: 'Yes, break it down into tasks',
      timestamp: new Date('2025-01-14T12:03:00'),
    },
    {
      id: 'dev4',
      role: 'agent',
      content:
        '✅ Created 6 technical enabler stories:\n\n1. Setup JWT authentication middleware\n2. Implement password hashing with bcrypt\n3. Create user registration endpoint\n4. Create login/logout endpoints\n5. Implement frontend AuthContext\n6. Add protected route guards\n\nAll tasks are linked to the "User Authentication" parent story.',
      agentType: 'DEVELOPER',
      timestamp: new Date('2025-01-14T12:04:00'),
    },
  ],

  TESTER: [
    {
      id: 'test1',
      role: 'user',
      content: 'Can you review the login feature that\'s in REVIEW status?',
      timestamp: new Date('2025-01-14T13:00:00'),
    },
    {
      id: 'test2',
      role: 'agent',
      content:
        'I\'ve reviewed the login feature implementation. Here\'s my test report:\n\n**✅ Passed Tests**:\n- User can login with valid credentials\n- Error message shows for invalid credentials\n- Password field is masked\n- Form validation works correctly\n\n**❌ Issues Found**:\n1. Login button remains enabled during API call (should be disabled)\n2. No loading spinner shown\n3. Error message doesn\'t clear on retry\n\nShould I move this back to IN_PROGRESS or create bug tickets?',
      agentType: 'TESTER',
      timestamp: new Date('2025-01-14T13:02:00'),
    },
    {
      id: 'test3',
      role: 'user',
      content: 'Create bug tickets for the issues',
      timestamp: new Date('2025-01-14T13:03:00'),
    },
    {
      id: 'test4',
      role: 'agent',
      content:
        '✅ Created 3 bug tickets:\n\n1. [BUG] Login button not disabled during submission\n2. [BUG] Missing loading indicator on login\n3. [BUG] Error message persists after retry\n\nAll bugs are linked to the parent "User Login" story and assigned HIGH priority.',
      agentType: 'TESTER',
      timestamp: new Date('2025-01-14T13:04:00'),
    },
  ],
}

// Helper to get conversation for a specific agent
export const getAgentConversation = (agentType: AgentType | 'ALL'): Message[] => {
  return MOCK_CONVERSATIONS[agentType] || []
}

// Helper to simulate typing indicator
export const createTypingMessage = (agentType: AgentType): Message => ({
  id: 'typing',
  role: 'agent',
  content: '',
  agentType,
  timestamp: new Date(),
  isTyping: true,
})
