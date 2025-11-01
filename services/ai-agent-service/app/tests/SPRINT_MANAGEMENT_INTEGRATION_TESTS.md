# 📋 SPRINT MANAGEMENT - INTEGRATION TEST CASES

## 📊 SPRINT STRUCTURE

### Sprint Data Model

```
Sprint (sprint.json)
├── sprint_id: "sprint-1"
├── sprint_number: 1
├── sprint_goal: "Sprint 1 deliverables"
├── start_date: "2025-10-15"
├── end_date: "2025-10-29"
├── velocity_plan: 29 (story points)
├── velocity_actual: 0 (story points)
├── assigned_items: [US-001, US-002, TASK-001, ...]
└── status: "Planned" | "Active" | "Completed"
```

### Sprint Fields

| Field | Type | Required | Description |
|---|---|---|---|
| sprint_id | string | ✅ | Format: sprint-1, sprint-2 |
| sprint_number | int | ✅ | Sequential number (1, 2, 3) |
| sprint_goal | string | ✅ | Main objective of sprint |
| start_date | date | ✅ | YYYY-MM-DD format |
| end_date | date | ✅ | YYYY-MM-DD format |
| velocity_plan | int | ✅ | Planned story points |
| velocity_actual | int | ✅ | Actual story points (0 initially) |
| assigned_items | list | ✅ | Item IDs assigned to sprint |
| status | string | ✅ | Planned, Active, or Completed |

---

## 🧪 INTEGRATION TEST CASES

### GROUP 1: SPRINT LOADING & PARSING

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-SM-01** | Load Sprint JSON | 1. Load sprint.json<br>2. Parse JSON<br>3. Validate structure<br>4. Count sprints | ✅ sprint.json loaded<br>✅ 1 sprint parsed<br>✅ Structure valid<br>✅ Sprint 1 found | sprint.json exists<br>Valid JSON format |
| **TC-SM-02** | Validate Sprint Fields | 1. Load sprint.json<br>2. Validate each sprint<br>3. Check required fields<br>4. Report missing fields | ✅ All sprints valid<br>✅ Required fields present<br>✅ No missing fields<br>✅ Validation passed | sprint.json exists<br>All sprints have required fields |
| **TC-SM-03** | Handle Invalid Sprint JSON | 1. Load corrupted sprint.json<br>2. Catch JSON error<br>3. Log error<br>4. Return error message | ✅ JSON parse error caught<br>✅ Error logged<br>✅ Graceful failure<br>✅ Error message returned | sprint.json corrupted |
| **TC-SM-04** | Handle Missing Sprint File | 1. Try to load sprint.json<br>2. Catch FileNotFoundError<br>3. Log error<br>4. Return error message | ✅ FileNotFoundError caught<br>✅ Error logged<br>✅ Graceful failure<br>✅ Error message returned | sprint.json missing |

### GROUP 2: SPRINT DATE VALIDATION

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-SM-05** | Validate Sprint Dates | 1. Load sprint.json<br>2. Check start_date < end_date<br>3. Check date format<br>4. Validate duration | ✅ Dates valid<br>✅ start_date < end_date<br>✅ Format correct (YYYY-MM-DD)<br>✅ Duration = 14 days | sprint.json loaded |
| **TC-SM-06** | Detect Invalid Date Range | 1. Load sprint.json<br>2. Find sprint with end_date < start_date<br>3. Report error<br>4. Return validation error | ✅ Invalid range detected<br>✅ Error message returned<br>✅ Error logged<br>✅ Graceful handling | sprint.json with invalid dates |
| **TC-SM-07** | Detect Overlapping Sprints | 1. Load sprint.json<br>2. Load multiple sprints<br>3. Check for date overlaps<br>4. Report overlaps | ✅ No overlaps detected<br>✅ Sprints sequential<br>✅ Validation passed<br>✅ Report returned | sprint.json with multiple sprints |
| **TC-SM-08** | Validate Sprint Duration | 1. Load sprint.json<br>2. Calculate duration<br>3. Check minimum duration<br>4. Report duration | ✅ Duration calculated<br>✅ Duration >= 1 day<br>✅ Duration = 14 days<br>✅ Validation passed | sprint.json loaded |

### GROUP 3: SPRINT VELOCITY MANAGEMENT

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-SM-09** | Load Sprint Velocity Plan | 1. Load sprint.json<br>2. Extract velocity_plan<br>3. Validate value<br>4. Return velocity | ✅ velocity_plan loaded<br>✅ velocity_plan = 29<br>✅ Value valid (> 0)<br>✅ Velocity returned | sprint.json loaded |
| **TC-SM-10** | Update Sprint Velocity Actual | 1. Load sprint.json<br>2. Find sprint by ID<br>3. Update velocity_actual<br>4. Save sprint.json | ✅ velocity_actual updated<br>✅ velocity_actual = 25<br>✅ sprint.json saved<br>✅ File persisted | sprint.json loaded<br>Sprint exists |
| **TC-SM-11** | Calculate Sprint Velocity from Items | 1. Load sprint.json<br>2. Load backlog.json<br>3. Filter assigned items<br>4. Sum story_points | ✅ Velocity calculated<br>✅ Only assigned items counted<br>✅ Total = 29 points<br>✅ Result returned | sprint.json & backlog.json loaded |
| **TC-SM-12** | Calculate Velocity Utilization | 1. Load sprint.json<br>2. Get velocity_plan<br>3. Get velocity_actual<br>4. Calculate utilization % | ✅ Utilization calculated<br>✅ Utilization = 86% (25/29)<br>✅ Percentage returned<br>✅ Validation passed | sprint.json loaded<br>velocity_actual set |

### GROUP 4: SPRINT CAPACITY PLANNING

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-SM-13** | Calculate Sprint Capacity | 1. Load sprint.json<br>2. Load backlog.json<br>3. Filter assigned items<br>4. Sum story_points | ✅ Capacity calculated<br>✅ Total = 29 points<br>✅ Capacity = 29 points<br>✅ Result returned | sprint.json & backlog.json loaded |
| **TC-SM-14** | Detect Capacity Overload | 1. Load sprint.json<br>2. Calculate total story_points<br>3. Compare with velocity_plan<br>4. Report overload | ✅ No overload detected<br>✅ Total <= velocity_plan<br>✅ Utilization = 100%<br>✅ Validation passed | sprint.json & backlog.json loaded |
| **TC-SM-15** | Detect Capacity Underload | 1. Load sprint.json<br>2. Calculate total story_points<br>3. Compare with velocity_plan<br>4. Report underload | ✅ Underload detected<br>✅ Total < velocity_plan<br>✅ Utilization < 100%<br>✅ Warning returned | sprint.json & backlog.json loaded |
| **TC-SM-16** | Calculate Capacity Percentage | 1. Load sprint.json<br>2. Load backlog.json<br>3. Calculate total story_points<br>4. Calculate percentage | ✅ Percentage calculated<br>✅ Percentage = 100%<br>✅ Result returned<br>✅ Validation passed | sprint.json & backlog.json loaded |

### GROUP 5: SPRINT ASSIGNMENT VALIDATION

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-SM-17** | Validate Sprint Assignments | 1. Load sprint.json<br>2. Load backlog.json<br>3. Validate assigned_items exist<br>4. Report missing items | ✅ All items exist<br>✅ No missing items<br>✅ 12 items verified<br>✅ Validation passed | sprint.json & backlog.json loaded |
| **TC-SM-18** | Detect Unassigned Items | 1. Load sprint.json<br>2. Load backlog.json<br>3. Find items not assigned<br>4. Return unassigned list | ✅ Unassigned items detected<br>✅ Count = 44 items<br>✅ List returned<br>✅ Validation passed | sprint.json & backlog.json loaded |
| **TC-SM-19** | Detect Duplicate Assignments | 1. Load sprint.json<br>2. Check assigned_items<br>3. Find duplicates<br>4. Report duplicates | ✅ No duplicates found<br>✅ All items unique<br>✅ Validation passed<br>✅ Report returned | sprint.json loaded |
| **TC-SM-20** | Validate Item Types in Sprint | 1. Load sprint.json<br>2. Load backlog.json<br>3. Check item types<br>4. Validate types | ✅ Item types valid<br>✅ Only Epic/US/Task assigned<br>✅ No Sub-tasks assigned<br>✅ Validation passed | sprint.json & backlog.json loaded |

### GROUP 6: SPRINT STATUS MANAGEMENT

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-SM-21** | Load Sprint Status | 1. Load sprint.json<br>2. Extract status field<br>3. Validate status value<br>4. Return status | ✅ Status loaded<br>✅ status = "Planned"<br>✅ Value valid<br>✅ Status returned | sprint.json loaded |
| **TC-SM-22** | Update Sprint Status to Active | 1. Load sprint.json<br>2. Find sprint by ID<br>3. Update status = "Active"<br>4. Save sprint.json | ✅ Status updated<br>✅ status = "Active"<br>✅ sprint.json saved<br>✅ File persisted | sprint.json loaded<br>Sprint exists |
| **TC-SM-23** | Update Sprint Status to Completed | 1. Load sprint.json<br>2. Find sprint by ID<br>3. Update status = "Completed"<br>4. Save sprint.json | ✅ Status updated<br>✅ status = "Completed"<br>✅ sprint.json saved<br>✅ File persisted | sprint.json loaded<br>Sprint exists |
| **TC-SM-24** | Validate Status Transitions | 1. Load sprint.json<br>2. Check current status<br>3. Validate next status<br>4. Allow/reject transition | ✅ Transition valid<br>✅ Planned → Active allowed<br>✅ Active → Completed allowed<br>✅ Validation passed | sprint.json loaded |

### GROUP 7: SPRINT DEPENDENCY VALIDATION

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-SM-25** | Detect Sprint Dependencies | 1. Load sprint.json<br>2. Load backlog.json<br>3. Find items with dependencies<br>4. Return dependency graph | ✅ Dependencies detected<br>✅ All dependency IDs valid<br>✅ Dependency graph built<br>✅ Graph returned | sprint.json & backlog.json loaded |
| **TC-SM-26** | Validate Dependencies in Sprint | 1. Load sprint.json<br>2. Load backlog.json<br>3. Check assigned items<br>4. Validate all deps in sprint | ✅ All dependencies in sprint<br>✅ No external dependencies<br>✅ Validation passed<br>✅ Report returned | sprint.json & backlog.json loaded |
| **TC-SM-27** | Detect Missing Dependencies | 1. Load sprint.json<br>2. Load backlog.json<br>3. Find items with external deps<br>4. Report missing deps | ✅ Missing deps detected<br>✅ Items identified<br>✅ Report returned<br>✅ Validation passed | sprint.json & backlog.json loaded |
| **TC-SM-28** | Resolve Dependency Order | 1. Load sprint.json<br>2. Load backlog.json<br>3. Build dependency graph<br>4. Return execution order | ✅ Execution order calculated<br>✅ Dependencies respected<br>✅ Order returned<br>✅ Validation passed | sprint.json & backlog.json loaded |

### GROUP 8: SPRINT METRICS & REPORTING

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-SM-29** | Calculate Sprint Burndown | 1. Load sprint.json<br>2. Load backlog.json<br>3. Calculate daily progress<br>4. Generate burndown data | ✅ Burndown calculated<br>✅ Daily data points<br>✅ Trend line generated<br>✅ Data returned | sprint.json & backlog.json loaded |
| **TC-SM-30** | Calculate Sprint Velocity Trend | 1. Load multiple sprints<br>2. Calculate velocity for each<br>3. Analyze trend<br>4. Return trend data | ✅ Trend calculated<br>✅ Velocity trend shown<br>✅ Forecast generated<br>✅ Data returned | Multiple sprints loaded |
| **TC-SM-31** | Generate Sprint Report | 1. Load sprint.json<br>2. Load backlog.json<br>3. Calculate metrics<br>4. Generate report | ✅ Report generated<br>✅ Metrics calculated<br>✅ Report formatted<br>✅ Report returned | sprint.json & backlog.json loaded |
| **TC-SM-32** | Calculate Sprint Completion % | 1. Load sprint.json<br>2. Load backlog.json<br>3. Count completed items<br>4. Calculate percentage | ✅ Completion % calculated<br>✅ Percentage = 0% (initial)<br>✅ Result returned<br>✅ Validation passed | sprint.json & backlog.json loaded |

### GROUP 9: SPRINT FILTERING & SEARCH

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-SM-33** | Filter Sprints by Status | 1. Load sprint.json<br>2. Filter by status="Planned"<br>3. Count matching sprints<br>4. Return filtered list | ✅ Sprints filtered<br>✅ Count = 1 sprint<br>✅ status = "Planned"<br>✅ List returned | sprint.json loaded |
| **TC-SM-34** | Sort Sprints by Number | 1. Load sprint.json<br>2. Sort by sprint_number<br>3. Verify order<br>4. Return sorted list | ✅ Sprints sorted<br>✅ Order: sprint-1, sprint-2, ...<br>✅ Ascending order<br>✅ List returned | Multiple sprints loaded |
| **TC-SM-35** | Search Sprint by Goal | 1. Load sprint.json<br>2. Search by goal text<br>3. Find matching sprints<br>4. Return results | ✅ Sprints found<br>✅ Goal text matched<br>✅ Results returned<br>✅ Search successful | sprint.json loaded |
| **TC-SM-36** | Filter Sprints by Date Range | 1. Load sprint.json<br>2. Filter by date range<br>3. Find sprints in range<br>4. Return filtered list | ✅ Sprints filtered<br>✅ Date range matched<br>✅ Results returned<br>✅ Filter successful | sprint.json loaded |

### GROUP 10: SPRINT COMPLETION & ARCHIVAL

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-SM-37** | Complete Sprint | 1. Load sprint.json<br>2. Find sprint by ID<br>3. Update status = "Completed"<br>4. Save sprint.json | ✅ Sprint completed<br>✅ status = "Completed"<br>✅ sprint.json saved<br>✅ File persisted | sprint.json loaded<br>Sprint exists |
| **TC-SM-38** | Archive Sprint Data | 1. Load sprint.json<br>2. Prepare archive data<br>3. Save to archive<br>4. Confirm archive | ✅ Sprint archived<br>✅ Data backed up<br>✅ Archive confirmed<br>✅ Archive successful | sprint.json loaded |
| **TC-SM-39** | Export Sprint to Database | 1. Load sprint.json<br>2. Transform data<br>3. Call database API<br>4. Save to database | ✅ Sprint exported<br>✅ Database API called<br>✅ Sprint saved<br>✅ Export successful | sprint.json loaded<br>Database connected |
| **TC-SM-40** | Publish Sprint Completion Event | 1. Load sprint.json<br>2. Prepare event data<br>3. Publish to message queue<br>4. Confirm publish | ✅ Event published<br>✅ Message queue received<br>✅ Event data correct<br>✅ Publish successful | sprint.json loaded<br>Message queue connected |

---

## 📊 TEST SUMMARY

| Category | Count | Status |
|---|---|---|
| **Sprint Loading & Parsing** | 4 | ✅ Ready |
| **Sprint Date Validation** | 4 | ✅ Ready |
| **Sprint Velocity Management** | 4 | ✅ Ready |
| **Sprint Capacity Planning** | 4 | ✅ Ready |
| **Sprint Assignment Validation** | 4 | ✅ Ready |
| **Sprint Status Management** | 4 | ✅ Ready |
| **Sprint Dependency Validation** | 4 | ✅ Ready |
| **Sprint Metrics & Reporting** | 4 | ✅ Ready |
| **Sprint Filtering & Search** | 4 | ✅ Ready |
| **Sprint Completion & Archival** | 4 | ✅ Ready |
| **TOTAL** | **40 Test Cases** | ✅ Ready |

---

## 🎯 IMPLEMENTATION PRIORITY

### Phase 1: Foundation (Critical)
- TC-SM-01 to TC-SM-04: Sprint Loading
- TC-SM-05 to TC-SM-08: Date Validation
- TC-SM-09 to TC-SM-12: Velocity Management

### Phase 2: Core Operations (High)
- TC-SM-13 to TC-SM-16: Capacity Planning
- TC-SM-17 to TC-SM-20: Assignment Validation
- TC-SM-21 to TC-SM-24: Status Management

### Phase 3: Advanced Features (Medium)
- TC-SM-25 to TC-SM-28: Dependencies
- TC-SM-29 to TC-SM-32: Metrics & Reporting
- TC-SM-33 to TC-SM-36: Filtering & Search

### Phase 4: Integration (Low)
- TC-SM-37 to TC-SM-40: Completion & Archival

