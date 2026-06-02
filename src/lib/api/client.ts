class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message)
    this.name = "ApiError"
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text().catch(() => "Unknown error")
    throw new ApiError(response.status, text)
  }
  return response.json() as Promise<T>
}

export const apiClient = {
  async get<T>(path: string): Promise<T> {
    const response = await fetch(path)
    return handleResponse<T>(response)
  },

  async post<T>(path: string, body?: FormData | Record<string, unknown>): Promise<T> {
    const isFormData = body instanceof FormData
    const response = await fetch(path, {
      method: "POST",
      ...(isFormData
        ? { body }
        : {
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }),
    })
    return handleResponse<T>(response)
  },

  async patch<T>(path: string, body: Record<string, unknown>): Promise<T> {
    const response = await fetch(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    return handleResponse<T>(response)
  },

  async delete<T>(path: string): Promise<T> {
    const response = await fetch(path, { method: "DELETE" })
    if (response.status === 204) return undefined as T
    return handleResponse<T>(response)
  },
}

