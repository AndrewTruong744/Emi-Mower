import client from './client';

export interface UserDataResponse {
  message: string;
  user_data: {
    id: string;
    email: string;
    name: string;
    created_at: string | null;
  } | null;
}

export interface UpdateUserEmailResponse {
  message: string;
  user_id: string;
  new_email: string | null;
}

export interface UpdateUserNameResponse {
  message: string;
  user_id: string;
  new_user_name: string | null;
}

export const getUserData = (userId: string): Promise<UserDataResponse> => {
  return client.get(`/protected/user/${userId}/data`);
};

export const postUserData = (userId: string): Promise<UserDataResponse> => {
  return client.post(`/protected/user/${userId}/data`);
};

export const patchUserEmail = (
  userId: string,
  newIdToken: string
): Promise<UpdateUserEmailResponse> => {
  return client.patch(`/protected/user/${userId}/email`, {
    new_id_token: newIdToken,
  });
};

export const patchUsername = (
  userId: string,
  newUserName: string
): Promise<UpdateUserNameResponse> => {
  return client.patch(`/protected/user/${userId}/name`, {
    new_user_name: newUserName,
  });
};
