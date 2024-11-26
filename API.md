# API Endpoints

## Root

### `GET /`

Hello world!

- **Request**: Any
- **Response**:
    - `200 OK`

## Teapot

### `GET /teapot`

"Wanna grab some coffee?"

- **Request**: Any
- **Response**:
    - `418` with HTML

## Database

### `POST /db/question/create`

**Rate Limited** - **Local Only**

Submit a new question to the database.

- **Request Body**:
    - `subject` (String): The subject of the question.
    - `description` (String): Detailed description of the question.
    - `opts` (String): Options for the question.
    - `ans` (String): Answer to the question.
    - `explanation` (Optional<String>): Explanation of the answer.
    - `details` (Optional<String>): Additional details for the question.
- **Responses**:
    - `200 OK`: Question successfully created.
    - `400 Bad Request`: A required field is missing (returns the name of the missing field).

## Send

### `/send/question`

**Rate Limited** - **Local Only**

Send a question to users who want to receive msg from bot.

- **Request**: Any
- **Response**:
  - `200 OK`

### `/send/answer`

**Rate Limited** - **Local Only**

Send an answer to users who want to receive msg from bot.

- **Request**: Any
- **Response**:
  - `200 OK`

### `/send/countdown`

**Rate Limited** - **Local Only**

Send a countdown message to users who want to receive msg from bot.

- **Request**: Any
- **Response**:
  - `200 OK`
