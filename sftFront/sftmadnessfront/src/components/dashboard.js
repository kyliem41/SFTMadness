import React, { useState, useEffect } from 'react';
import { signOut } from 'aws-amplify/auth';

import { userService } from '../services/api/userService';
import { UserProfileForm } from './users/profile';
import { ForgotPasswordForm } from './users/forgotPass';
import { ConfirmPasswordResetForm } from './users/confirmPassRe';
import { DeleteAccountForm } from './users/deleteUser';

import { SchoolContactProfile } from './schoolContact/schoolContactProfile';
import { CreateContact } from './schoolContact/createSchoolContact';

import { FileManagement } from './files/fileManager';

import { ScrapedFileManagement } from './scrapedFiles/scrapedFileManager';

import { Calender } from './events/calender';

import { EmailForm } from './email/emailForm';

import { CustomsManager } from './customs/customForm';

import { ConversationLogs } from './conversationLogs/conversationLogs';
import { Button, ButtonGroup } from '@mui/material';

import './adminDashboard.css';

//customer dashboard
export const Dashboard = ({ onSignOut }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('profile');

  //password reset state - not yet implemented
  const [passwordResetEmail, setPasswordResetEmail] = useState('');
  const [showPasswordResetConfirmation, setShowPasswordResetConfirmation] = useState(false);
  
  //school contact state
  const [contactId, setContactId] = useState('');
  const [showContactIdInput, setShowContactIdInput] = useState(false);

  useEffect(() => {
    fetchUser();
  }, []);

  //user handlers
  //fetch user data handler
  const fetchUser = async () => {
    try {
      setLoading(true);
      setError('');

      const userData = await userService.getCurrentUser();
      
      console.log('User data loaded:', userData);
      
      setUser(userData);
      
      if (userData.createdFromCognito) {
        setError('Some profile information could not be loaded from the database. You can still update your profile.');
      }
    } catch (err) {
      console.error('Error fetching user data:', err);
      setError('Failed to load complete user data. Using basic profile information.');
      
      try {
        // fallback to cognito user data
        const cognitoUser = await userService.getCurrentUser();
        setUser({
          email: cognitoUser.username,
          username: cognitoUser.username,
          userId: cognitoUser.userId,
          companyName: '',
          phoneNumber: '',
          id: '1',
          createdFromCognito: true
        });
      } catch (cognitoErr) {
        console.error('Failed to get Cognito user data:', cognitoErr);
        setError('Failed to load user data. Please sign in again.');
      }
    } finally {
      setLoading(false);
    }
  };

  //sign out handler
  const handleSignOut = async () => {
    try {
      await signOut();
      
      if (onSignOut) {
        onSignOut();
      } else {
        //fallback if onSignOut prop not provided
        window.location.href = '/';
      }
    } catch (error) {
      console.error('Sign out error:', error);
      setError('Error signing out. Please try again.');
    }
  };

  //delete account handler
  const handleDeleteSuccess = () => {
    if (onSignOut) {
      onSignOut();
    } else {
      window.location.href = '/';
    }
  };

  // //password reset handlers
  // const handlePasswordResetRequest = (email) => {
  //   setPasswordResetEmail(email);
  //   setShowPasswordResetConfirmation(true);
  // };

  //password reset success handler
  const handlePasswordResetSuccess = () => {
    setShowPasswordResetConfirmation(false);
    setActiveTab('profile');
    alert('Password has been reset successfully. Please log in with your new password.');
    handleSignOut();
  };

  //school contact handlers
  //contact id input handlers
  const handleContactIdChange = (e) => {
    setContactId(e.target.value);
  };

  //contact id submission handler
  const handleContactIdSubmit = (e) => {
    e.preventDefault();
    const contactIdStr = String(contactId);
  
    if (contactIdStr.trim()) {
      setShowContactIdInput(false);
    } else {
      setError('Please enter a valid contact ID');
    }
  };
  
  //contact creation handler
  const handleContactCreated = (newContact) => {
    setContactId(newContact.id);
    setActiveTab('view-contact');
    alert(`Contact created with ID: ${newContact.id}`);
  };
  
  //contact update handler
  const handleContactUpdate = () => {
    alert('Contact updated successfully!');
  };
  
  //contact delete handler
  const handleContactDelete = () => {
    setContactId('');
    setActiveTab('profile');
    alert('Contact deleted successfully!');
  };

  //loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  //get display name
  const displayName = user?.username || user?.email || 'User';

  return (
    <div className="">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-xl shadow-md overflow-hidden p-6 mb-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-blue-600">
              Welcome, {displayName}
            </h1>
            {/* Profile Tab */}
            <Button
            variant='contained'
            color='secondary'
              onClick={handleSignOut}
              className="SignOutBtn"
            >
              Sign out
            </Button>
          </div>

          {error && (
            <div className="">
              {error}
            </div>
          )}
 
          <div className="">
            <nav className="">
              <ButtonGroup color='warning'  className='BtnGroup3' size='small'>
              <Button
              variant='contained'
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'profile'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab('profile')}
              >
                Profile
              </Button>

              {/* Password Reset Tab */}
              <Button
              variant='contained'
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'password'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab('password')}
              >
                Reset Password
              </Button>
              <Button
              variant='contained'
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'delete'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab('delete')}
              >
                Delete Account
              </Button>
              
              {/* File Management Tab */}
              <Button
              variant='contained'
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'files'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab('files')}
              >
                Files
              </Button>

              {/* Scraped File Management Tab */}
              <Button
              variant='contained'
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'scrapedFiles'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab('scrapedFiles')}
              >
                Scraped Files
              </Button>
              
              {/* School Contact Tab */}
              <Button
              variant='contained'
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'create-contact'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => {
                  setActiveTab('create-contact');
                  setShowContactIdInput(false);
                }}
              >
                Create Contact
              </Button>
              <Button
              variant='contained'
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'view-contact'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => {
                  setActiveTab('view-contact');
                  setShowContactIdInput(true);
                }}
              >
                View Contact
              </Button>

              {/* Calender Tab */}
              <Button
              variant='contained'
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'events'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab('events')}
              >
                Events
              </Button>
              
              {/* Email Tab */}
              <Button
              variant='contained'
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'email'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setActiveTab('email')}
            >
              Email
            </Button>

            {/* Customs Tab */}
            <Button
            variant='contained'
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'customs'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
            onClick={() => setActiveTab('customs')}
            >
              AI Settings
            </Button>

            {/* Conversation Logs Tab */}
            <Button
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'logs'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              variant='contained'
              onClick={() => setActiveTab('logs')}
            >
              Conversation Logs
            </Button>
            </ButtonGroup>
            </nav>
          </div>

          {/* ***************************************************** */}
          {/* Dashboard Content - Components */}
          {/* ***************************************************** */}

          <div className="mt-6">
            {/* Profile Component */}
            {activeTab === 'profile' && (
              <UserProfileForm 
                user={user}
                onProfileUpdate={fetchUser}
              />
            )}

            {/* Password Reset Component */}
            {activeTab === 'password' && (
              <>
                {showPasswordResetConfirmation ? (
                  <ConfirmPasswordResetForm
                    email={passwordResetEmail}
                    userId={user.id}
                    onSuccess={handlePasswordResetSuccess}
                    onCancel={() => setShowPasswordResetConfirmation(false)}
                  />
                ) : (
                  <ForgotPasswordForm 
                    onSuccess={(email, userId) => {
                      setPasswordResetEmail(email);
                      setShowPasswordResetConfirmation(true);
                    }}
                    defaultEmail={user?.email}
                  />
                )}
              </>
            )}
            
            {/* Delete Profile Component */}
            {activeTab === 'delete' && (
              <DeleteAccountForm 
                onSuccess={handleDeleteSuccess} 
                user={user}
              />
            )}
            
            {/* File Management Component */}
            {activeTab === 'files' && (
              <FileManagement />
            )}

            {/* Scraped File Management Component */}
            {activeTab === 'scrapedFiles' && (
              <ScrapedFileManagement />
            )}
            
            {/* School Contact Components */}
            {/* Create Contact Component */}
            {activeTab === 'create-contact' && (
              <CreateContact onSuccess={handleContactCreated} />
            )}
            
            {/* View Contact Component */}
            {activeTab === 'view-contact' && (
              <>
                {showContactIdInput && (
                  <div className="mb-6">
                    <form onSubmit={handleContactIdSubmit} className="flex space-x-2">
                      <input
                        type="text"
                        value={contactId}
                        onChange={handleContactIdChange}
                        placeholder="Enter Contact ID"
                        className="flex-1 p-2 border rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <button
                        type="submit"
                        className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
                      >
                        Load Contact
                      </button>
                    </form>
                  </div>
                )}
                
                {/* Contact Profile Component */}
                {contactId ? (
                  <SchoolContactProfile
                    contactId={contactId}
                    onUpdate={handleContactUpdate}
                    onDelete={handleContactDelete}
                  />
                ) : !showContactIdInput && (
                  <div className="text-center py-8 text-gray-500">
                    No contact ID provided. Please use the "View Contact" tab to enter an ID.
                  </div>
                )}
              </>
            )}

              {/* Calender Component */}
                {activeTab === 'events' && (
                <Calender />
              )}

              {/* Email Component */}
              {activeTab === 'email' && (
                <EmailForm />
              )}

              {/* Customs Component */}
              {activeTab === 'customs' && (
                <CustomsManager />
              )}

              {/* Conversation Logs Component */}
              {activeTab === 'logs' && (
                <ConversationLogs />
              )}

          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;