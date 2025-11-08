function loginResponseDto(user, token) {
  return {
    user: {
      id: user._id,
      email: user.email,
      is_verified: user.is_verified
    },
    token
  };
}

module.exports = loginResponseDto;