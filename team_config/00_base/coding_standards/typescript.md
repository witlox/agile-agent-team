# TypeScript Coding Standards

## Enforced by Tools

All TypeScript code MUST conform to these tool-enforced standards:

### 1. Prettier (Formatter)
- **THE STANDARD** for JS/TS formatting
- **Line length**: 80-100 characters (configurable, default 80)
- **Quotes**: Single quotes (configurable)
- **Semicolons**: Always (configurable)
- **Trailing commas**: ES5 compatible
- Run: `prettier --write .`
- Config in `.prettierrc`:
```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "printWidth": 100,
  "trailingComma": "es5"
}
```

### 2. ESLint (Linter)
- **THE LINTER** for TypeScript
- Use `@typescript-eslint` plugin
- Recommended: Airbnb or Standard config as base
- Run: `eslint . --ext .ts,.tsx`
- Config in `.eslintrc.json`:
```json
{
  "parser": "@typescript-eslint/parser",
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "prettier"
  ],
  "rules": {
    "@typescript-eslint/explicit-function-return-type": "error",
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/no-unused-vars": "error"
  }
}
```

### 3. TypeScript Compiler (tsc)
- **Strict mode REQUIRED**: All strict flags enabled
- Run: `tsc --noEmit` (type check without emitting)
- Config in `tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "strict": true,                          // REQUIRED
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "noImplicitAny": true,                   // Part of strict
    "strictNullChecks": true,                // Part of strict
    "strictFunctionTypes": true,             // Part of strict
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

### 4. Jest (Testing)
- Standard testing framework for TypeScript
- Test files: `*.test.ts` or `*.spec.ts`
- **Coverage requirement**: ≥85%
- Run: `jest --coverage`
- Config in `jest.config.js`:
```javascript
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 85,
      lines: 85,
      statements: 85
    }
  }
};
```

## Non-Negotiable Patterns

### Naming Conventions (Enforced by ESLint)
```typescript
// Interfaces and Types: PascalCase
interface UserAccount {}
type Status = 'active' | 'inactive';

// Classes: PascalCase
class UserService {}

// Functions and variables: camelCase
function getUserById(id: number): User {}
const userCount = 42;

// Constants: UPPER_SNAKE_CASE
const MAX_RETRIES = 3;
const API_ENDPOINT = 'https://api.example.com';

// Private class members: prefix with # (or _)
class User {
  #password: string;  // Truly private
  _cache: Map<string, any>;  // Convention for "private"
}

// Enums: PascalCase for name, PascalCase for members
enum OrderStatus {
  Pending,
  Processing,
  Completed
}
```

### Type Annotations (REQUIRED)
```typescript
// All function parameters and return types MUST be typed
function calculateTotal(
  items: Item[],
  taxRate: number
): number {
  return items.reduce((sum, item) => sum + item.price, 0) * (1 + taxRate);
}

// Use explicit return types (not inferred)
function getUser(id: number): Promise<User | null> {
  // Implementation
}

// Avoid 'any' - use 'unknown' if type is truly unknown
function processData(data: unknown): void {
  if (typeof data === 'string') {
    console.log(data.toUpperCase());
  }
}

// Use const assertions for literals
const CONFIG = {
  maxRetries: 3,
  timeout: 5000,
} as const;  // Type is { readonly maxRetries: 3; readonly timeout: 5000 }
```

### Error Handling (Standard Pattern)
```typescript
// Custom error classes
class UserNotFoundError extends Error {
  constructor(public userId: number) {
    super(`User ${userId} not found`);
    this.name = 'UserNotFoundError';
  }
}

// Async error handling with Result type (recommended)
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

async function getUser(id: number): Promise<Result<User>> {
  try {
    const user = await fetchUser(id);
    return { ok: true, value: user };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error : new Error(String(error))
    };
  }
}

// Usage
const result = await getUser(123);
if (result.ok) {
  console.log(result.value.name);
} else {
  console.error(result.error.message);
}
```

### Null Safety (strictNullChecks)
```typescript
// ALWAYS handle null/undefined explicitly
function findUser(id: number): User | undefined {
  return users.find(u => u.id === id);
}

// Use optional chaining and nullish coalescing
const userName = user?.profile?.name ?? 'Anonymous';

// Type guards for narrowing
function isUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'email' in value
  );
}

if (isUser(data)) {
  console.log(data.email);  // TypeScript knows data is User
}
```

### Testing Pattern (Jest)
```typescript
import { UserService } from './user-service';
import { User } from './user';

describe('UserService', () => {
  let service: UserService;

  beforeEach(() => {
    service = new UserService();
  });

  describe('createUser', () => {
    it('should create user with valid email', async () => {
      const user = await service.createUser('test@example.com', 'John Doe');

      expect(user.email).toBe('test@example.com');
      expect(user.name).toBe('John Doe');
      expect(user.id).toBeDefined();
    });

    it('should throw error for invalid email', async () => {
      await expect(
        service.createUser('invalid-email', 'John Doe')
      ).rejects.toThrow('Invalid email');
    });

    it('should throw error for duplicate email', async () => {
      await service.createUser('test@example.com', 'John Doe');

      await expect(
        service.createUser('test@example.com', 'Jane Doe')
      ).rejects.toThrow('Email already exists');
    });
  });
});

// Mock dependencies
jest.mock('./database');
import { Database } from './database';

const mockDatabase = Database as jest.MockedClass<typeof Database>;
```

### Documentation (JSDoc/TSDoc)
```typescript
/**
 * Retrieves a user by their unique identifier.
 *
 * @param id - The unique user identifier
 * @returns Promise resolving to the user, or null if not found
 * @throws {DatabaseError} If database query fails
 *
 * @example
 * ```typescript
 * const user = await getUser(123);
 * if (user) {
 *   console.log(user.email);
 * }
 * ```
 */
async function getUser(id: number): Promise<User | null> {
  // Implementation
}
```

### Async/Await (Preferred Over Promises)
```typescript
// GOOD: Use async/await
async function fetchUserData(id: number): Promise<UserData> {
  const user = await getUser(id);
  const posts = await getPosts(user.id);
  const comments = await getComments(user.id);

  return { user, posts, comments };
}

// Parallel async operations
async function fetchMultipleUsers(ids: number[]): Promise<User[]> {
  return Promise.all(ids.map(id => getUser(id)));
}

// Error handling with try/catch
async function processUser(id: number): Promise<void> {
  try {
    const user = await getUser(id);
    await updateUser(user);
    console.log('User processed successfully');
  } catch (error) {
    if (error instanceof UserNotFoundError) {
      console.warn(`User ${id} not found`);
    } else {
      console.error('Failed to process user:', error);
      throw error;
    }
  }
}
```

### Type Utilities (Leverage TypeScript Features)
```typescript
// Use built-in utility types
type PartialUser = Partial<User>;  // All properties optional
type ReadonlyUser = Readonly<User>;  // All properties readonly
type UserEmail = Pick<User, 'email'>;  // Only email property
type UserWithoutPassword = Omit<User, 'password'>;  // All except password

// Discriminated unions for state machines
type LoadingState = { status: 'loading' };
type SuccessState = { status: 'success'; data: User[] };
type ErrorState = { status: 'error'; error: Error };

type State = LoadingState | SuccessState | ErrorState;

function handleState(state: State): void {
  switch (state.status) {
    case 'loading':
      console.log('Loading...');
      break;
    case 'success':
      console.log('Data:', state.data);  // TypeScript knows data exists
      break;
    case 'error':
      console.error('Error:', state.error);  // TypeScript knows error exists
      break;
  }
}
```

## Toolchain Commands

```bash
# Format code (ALWAYS run before commit)
prettier --write .

# Lint code
eslint . --ext .ts,.tsx --fix

# Type check
tsc --noEmit

# Run tests with coverage
jest --coverage

# All checks (CI pipeline)
prettier --check . && eslint . --ext .ts,.tsx && tsc --noEmit && jest --coverage
```

## TypeScript Best Practices

1. **Enable strict mode** - Always use `"strict": true` in tsconfig.json
2. **Avoid `any`** - Use `unknown` if type is truly unknown
3. **Use const assertions** - For literal types: `as const`
4. **Prefer interfaces over types** - For object shapes (better error messages)
5. **Use discriminated unions** - For state machines and variants
6. **Leverage type inference** - But be explicit for function returns
7. **Use readonly** - For immutable data
8. **Prefer composition over inheritance** - Use interfaces and mixins

## Deviations Allowed Only For

1. **Line length**: Can exceed 100 chars for:
   - Long type definitions
   - Complex JSX attributes

2. **`any` type**: Can use only for:
   - Third-party libraries without types
   - Gradual migration from JavaScript (temporarily)

3. **Test coverage**: Can be <85% for:
   - Defensive error handling
   - Browser-specific code

**All deviations MUST be justified with `// eslint-disable-next-line` comments.**

## Common Mistakes to Avoid

```typescript
// BAD: Using 'any'
function process(data: any) {
  return data.value;
}

// GOOD: Use proper types or 'unknown'
function process(data: unknown): string {
  if (isValidData(data)) {
    return data.value;
  }
  throw new Error('Invalid data');
}

// BAD: Not handling null/undefined
function getUserName(user: User | undefined) {
  return user.name;  // Error: user might be undefined
}

// GOOD: Handle null/undefined
function getUserName(user: User | undefined): string {
  return user?.name ?? 'Unknown';
}

// BAD: Mutation of readonly data
const config: Readonly<Config> = getConfig();
config.port = 8080;  // Error

// GOOD: Create new object
const newConfig = { ...config, port: 8080 };

// BAD: Non-null assertion without check
const user = users.find(u => u.id === id)!;  // Dangerous

// GOOD: Handle undefined case
const user = users.find(u => u.id === id);
if (!user) {
  throw new Error('User not found');
}
```

## React/Frontend Specific (if applicable)

```typescript
// Use functional components with TypeScript
interface Props {
  userId: number;
  onUpdate: (user: User) => void;
}

const UserProfile: React.FC<Props> = ({ userId, onUpdate }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUser(userId).then(setUser).finally(() => setLoading(false));
  }, [userId]);

  if (loading) return <div>Loading...</div>;
  if (!user) return <div>User not found</div>;

  return <div>{user.name}</div>;
};
```
