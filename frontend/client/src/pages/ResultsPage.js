import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Container, 
  Typography, 
  Tabs, 
  Tab, 
  Paper, 
  Alert,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Divider,
  Chip
} from '@mui/material';
import { useLocation } from 'react-router-dom';
import GraphVisualization from '../components/GraphVisualization';
import AdvancedGraphVisualization from '../components/AdvancedGraphVisualization';

const ResultsPage = () => {
  const location = useLocation();
  const [activeTab, setActiveTab] = useState(0);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [enhancedGraphData, setEnhancedGraphData] = useState({ nodes: [], links: [] });
  const [profileData, setProfileData] = useState(null);

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  useEffect(() => {
    // Get profile data from location state
    if (location.state && location.state.profileData) {
      const data = location.state.profileData;
      console.log("Received profile data:", data);
      
      // Use the actual data directly - don't enhance with fake data
      setProfileData(data);
      transformDataToGraph(data);
    }
  }, [location.state]);
  
  // Check if the data has minimum required fields for visualization
  const checkSufficientData = (data) => {
    // Check if there's at least a name and one experience or one skill
    const hasName = data && data.name && data.name !== 'Profile';
    const hasExperience = data && data.experiences && Array.isArray(data.experiences) && data.experiences.length > 0;
    const hasSkills = data && data.skills && Array.isArray(data.skills) && data.skills.length > 0;
    
    return hasName && (hasExperience || hasSkills);
  };
  
  // Keep the enhanceWithSampleData function but don't use it in the main flow
  const enhanceWithSampleData = (data) => {
    // Start with the original data or an empty object
    const enhancedData = { ...data } || {};
    
    // Keep the original name if available, otherwise use a placeholder
    enhancedData.name = data?.name || 'Your Profile';
    
    // Keep original headline or use placeholder
    enhancedData.headline = data?.headline || 'Professional with experience in technology';
    
    // Ensure there are experiences
    if (!enhancedData.experiences || !Array.isArray(enhancedData.experiences) || enhancedData.experiences.length === 0) {
      enhancedData.experiences = [
        {
          title: 'Technical Role',
          company: 'Technology Company',
          startDate: '2020-01',
          endDate: 'Present',
          description: 'Working on technical projects and solutions'
        },
        {
          title: 'Previous Role',
          company: 'Previous Company',
          startDate: '2018-01',
          endDate: '2019-12',
          description: 'Worked on various projects and initiatives'
        }
      ];
    }
    
    // Ensure there are skills
    if (!enhancedData.skills || !Array.isArray(enhancedData.skills) || enhancedData.skills.length === 0) {
      enhancedData.skills = [
        { name: 'Technical Skills', endorsements: 10 },
        { name: 'Problem Solving', endorsements: 8 },
        { name: 'Communication', endorsements: 12 }
      ];
    }
    
    // Ensure there is education
    if (!enhancedData.education || !Array.isArray(enhancedData.education) || enhancedData.education.length === 0) {
      enhancedData.education = [
        {
          school: 'University',
          degree: 'Degree',
          fieldOfStudy: 'Field of Study',
          startDate: '2014-09',
          endDate: '2018-05'
        }
      ];
    }
    
    return enhancedData;
  };

  // Transform the profile data into graph format
  const transformDataToGraph = (data) => {
    if (!data) return;

    try {
      console.log("Transforming data to graph:", data);
      
      // Initialize arrays for graph nodes and links
      const nodes = [];
      const links = [];
      
      // Get the actual profile data from the API response
      const profile = data.profile || data.fastApiResponse?.profile || data;
      console.log("Using profile data:", profile);
      
      // Create basic graph data (person and company connections)
      
      // Add person node
      const personId = `person-${profile.profile_id || profile.member_urn || profile.urn_id || '1'}`;
      nodes.push({
        id: personId,
        label: profile.first_name && profile.last_name 
          ? `${profile.first_name} ${profile.last_name}` 
          : (profile.name || 'Your Profile'),
        type: 'person',
        size: 20,
        description: profile.headline || profile.summary || 'Professional'
      });
      
      // Add company nodes and links for work experiences
      const experiences = profile.experience || profile.experiences || [];
      if (experiences && Array.isArray(experiences)) {
        console.log("Processing experiences:", experiences);
        
        // Process each experience to extract company data
        const processedExperiences = experiences.map(exp => {
          // Handle different company data structures
          let companyName, companyUrn, companyId;
          
          if (exp.company) {
            if (typeof exp.company === 'string') {
              companyName = exp.company;
              companyUrn = `company-${companyName.replace(/\s+/g, '')}`;
              companyId = companyUrn.replace(/[^a-zA-Z0-9]/g, '');
            } else {
              companyName = exp.company.name || 'Unknown Company';
              companyUrn = exp.company.urn || `company-${companyName.replace(/\s+/g, '')}`;
              companyId = companyUrn.replace(/[^a-zA-Z0-9]/g, '');
            }
          } else {
            companyName = 'Unknown Company';
            companyUrn = `company-unknown`;
            companyId = 'companyunknown';
          }
          
          return {
            ...exp,
            processedCompany: {
              name: companyName,
              urn: companyUrn,
              id: `node-${companyId}`
            }
          };
        });
        
        // Sort experiences by date if available
        const sortedExperiences = [...processedExperiences].sort((a, b) => {
          // Handle different date formats
          const getDate = (exp) => {
            if (exp.time_period && exp.time_period.start_date) {
              return new Date(
                exp.time_period.start_date.year, 
                (exp.time_period.start_date.month || 1) - 1
              );
            } else if (exp.startDate) {
              return new Date(exp.startDate);
            }
            return new Date(0);
          };
          
          return getDate(b) - getDate(a);
        });
        
        console.log("Sorted experiences:", sortedExperiences);
        
        // Add all company nodes
        sortedExperiences.forEach((exp, index) => {
          const companyId = exp.processedCompany.id;
          const companyName = exp.processedCompany.name;
          
          // Add company node if it doesn't exist
          if (!nodes.some(node => node.id === companyId)) {
            nodes.push({
              id: companyId,
              label: companyName,
              type: 'company',
              size: 15,
              description: exp.description || ''
            });
          }
          
          // Add link from person to company
          links.push({
            source: personId,
            target: companyId,
            value: 2,
            label: exp.title || 'Worked at'
          });
        });
        
        // Add career progression links between companies
        for (let i = 0; i < sortedExperiences.length - 1; i++) {
          const currentCompanyId = sortedExperiences[i].processedCompany.id;
          const nextCompanyId = sortedExperiences[i+1].processedCompany.id;
          
          links.push({
            source: nextCompanyId,
            target: currentCompanyId,
            value: 1.5,
            label: 'Career Progression'
          });
        }
      }
      
      console.log("Generated nodes:", nodes);
      console.log("Generated links:", links);
      
      // Set basic graph data
      setGraphData({ nodes, links });
      
      // Create enhanced graph data (with skills, education, projects, certifications)
      const enhancedNodes = [...nodes];
      const enhancedLinks = [...links];
      
      // Add skill nodes and links
      const skills = profile.skills || [];
      if (skills && Array.isArray(skills)) {
        // Add skill nodes
        skills.forEach((skill, index) => {
          // Handle different skill formats
          const skillName = typeof skill === 'string' ? skill : (skill.name || `Skill ${index + 1}`);
          const skillId = `skill-${skillName.replace(/\s+/g, '').replace(/[^a-zA-Z0-9]/g, '')}-${index}`;
          
          // Add skill node
          enhancedNodes.push({
            id: skillId,
            label: skillName,
            type: 'skill',
            size: 10
          });
          
          // Add link from person to skill
          enhancedLinks.push({
            source: personId,
            target: skillId,
            value: 1,
            label: 'Has Skill'
          });
        });
      }
      
      // Add education nodes and links
      const education = profile.education || [];
      if (education && Array.isArray(education)) {
        education.forEach((edu, index) => {
          // Handle different education formats
          let schoolName;
          if (typeof edu.school === 'string') {
            schoolName = edu.school;
          } else if (edu.school && edu.school.name) {
            schoolName = edu.school.name;
          } else {
            schoolName = edu.name || `Education ${index + 1}`;
          }
          
          const schoolId = `school-${schoolName.replace(/\s+/g, '').replace(/[^a-zA-Z0-9]/g, '')}-${index}`;
          
          // Add education node
          enhancedNodes.push({
            id: schoolId,
            label: schoolName,
            type: 'education',
            size: 12,
            description: edu.degree_name || edu.field_of_study || edu.fieldOfStudy || ''
          });
          
          // Add link from person to education
          enhancedLinks.push({
            source: personId,
            target: schoolId,
            value: 1.5,
            label: edu.degree_name || edu.degree || 'Studied at'
          });
        });
      }
      
      console.log("Enhanced nodes:", enhancedNodes);
      console.log("Enhanced links:", enhancedLinks);
      
      // Set enhanced graph data
      setEnhancedGraphData({ nodes: enhancedNodes, links: enhancedLinks });
    } catch (error) {
      console.error("Error transforming data to graph:", error);
    }
  };

  // Generate a placeholder/demo data if none exists
  const generateDemoData = () => {
    const demoProfileData = {
      id: 'demo123',
      name: 'Alex Morgan',
      headline: 'Technology Leader with 15+ years experience across startups and enterprise',
      experiences: [
        {
          title: 'Chief Technology Officer',
          company: 'FutureTech AI',
          startDate: '2022-01',
          endDate: 'Present',
          description: 'Leading technology strategy and AI product development for a Series B startup focused on enterprise AI solutions'
        },
        {
          title: 'VP of Engineering',
          company: 'DataSphere',
          startDate: '2019-04',
          endDate: '2021-12',
          description: 'Scaled engineering team from 30 to 120, implemented agile methodologies, and rebuilt cloud infrastructure'
        },
        {
          title: 'Senior Engineering Manager',
          company: 'TechNova',
          startDate: '2017-06',
          endDate: '2019-03',
          description: 'Led multiple product engineering teams, launched three major products, and drove technology standardization'
        },
        {
          title: 'Software Engineering Lead',
          company: 'GlobalTech',
          startDate: '2014-08',
          endDate: '2017-05',
          description: 'Managed a team of 15 engineers, architected microservices infrastructure, and implemented CI/CD pipelines'
        },
        {
          title: 'Senior Software Engineer',
          company: 'InnovateLabs',
          startDate: '2012-03',
          endDate: '2014-07',
          description: 'Developed high-performance trading algorithms and real-time analytics platforms for financial services'
        },
        {
          title: 'Software Engineer',
          company: 'StartupXYZ',
          startDate: '2010-06',
          endDate: '2012-02',
          description: 'Built scalable backend systems and APIs for the company\'s mobile and web applications'
        },
        {
          title: 'Junior Developer',
          company: 'TechCorp',
          startDate: '2008-07',
          endDate: '2010-05',
          description: 'Developed features for enterprise content management system and improved performance by 40%'
        }
      ],
      skills: [
        { name: 'Engineering Leadership', endorsements: 42 },
        { name: 'System Architecture', endorsements: 38 },
        { name: 'Artificial Intelligence', endorsements: 27 },
        { name: 'Machine Learning', endorsements: 31 },
        { name: 'Cloud Infrastructure', endorsements: 35 },
        { name: 'DevOps', endorsements: 29 },
        { name: 'Agile Methodologies', endorsements: 33 },
        { name: 'Python', endorsements: 25 },
        { name: 'JavaScript', endorsements: 22 },
        { name: 'Java', endorsements: 20 },
        { name: 'Kubernetes', endorsements: 19 },
        { name: 'AWS', endorsements: 28 },
        { name: 'Product Development', endorsements: 26 },
        { name: 'Data Science', endorsements: 18 },
        { name: 'Microservices', endorsements: 23 },
        { name: 'Team Building', endorsements: 30 }
      ],
      education: [
        {
          school: 'Stanford University',
          degree: 'MBA',
          fieldOfStudy: 'Technology Management',
          startDate: '2015-09',
          endDate: '2017-06',
          description: 'Part-time executive MBA program focused on technology management and entrepreneurship'
        },
        {
          school: 'MIT',
          degree: 'MS',
          fieldOfStudy: 'Computer Science',
          startDate: '2006-09',
          endDate: '2008-05',
          description: 'Specialized in artificial intelligence and distributed systems'
        },
        {
          school: 'UC Berkeley',
          degree: 'BS',
          fieldOfStudy: 'Computer Science',
          startDate: '2002-09',
          endDate: '2006-05',
          description: 'Minor in Mathematics'
        }
      ],
      certifications: [
        {
          name: 'AWS Solutions Architect Professional',
          issuer: 'Amazon Web Services',
          date: '2020-05'
        },
        {
          name: 'Google Cloud Professional Data Engineer',
          issuer: 'Google',
          date: '2019-08'
        },
        {
          name: 'Certified Kubernetes Administrator',
          issuer: 'Cloud Native Computing Foundation',
          date: '2018-11'
        }
      ],
      projects: [
        {
          name: 'Enterprise AI Platform',
          description: 'Led development of an enterprise AI platform serving 200+ customers',
          technologies: ['Python', 'TensorFlow', 'AWS', 'Kubernetes']
        },
        {
          name: 'Real-time Analytics Engine',
          description: 'Built a scalable real-time analytics engine processing 500M events daily',
          technologies: ['Java', 'Apache Kafka', 'ElasticSearch', 'Redis']
        },
        {
          name: 'Cloud Migration Framework',
          description: 'Developed a framework to migrate legacy systems to cloud infrastructure',
          technologies: ['AWS', 'Terraform', 'Docker', 'Python']
        }
      ]
    };
    
    setProfileData(demoProfileData);
    transformDataToGraph(demoProfileData);
  };

  useEffect(() => {
    // If no data is available, generate demo data
    if (!profileData && !location.state?.profileData) {
      generateDemoData();
    }
  }, [profileData, location.state]);

  // Render detailed profile information
  const renderProfileDetails = () => {
    if (!profileData) {
      return (
        <Alert severity="info">No profile data available.</Alert>
      );
    }

    return (
      <Card sx={{ bgcolor: 'background.paper', color: 'text.primary' }}>
        <CardContent>
          <Typography variant="h4" gutterBottom>
            {profileData.name || 'Profile'}
          </Typography>
          
          <Typography variant="subtitle1" sx={{ mb: 2, color: 'primary.main' }}>
            {profileData.headline || ''}
          </Typography>
          
          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            Work Experience
          </Typography>
          <Divider sx={{ mb: 2 }} />
          
          {profileData.experiences && profileData.experiences.length > 0 ? (
            <List>
              {profileData.experiences.map((exp, index) => (
                <ListItem key={index} sx={{ display: 'block', mb: 2 }}>
                  <Typography variant="subtitle2" color="primary.main">
                    {exp.title || 'Role'}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {exp.company || 'Company'}
                    {exp.startDate && exp.endDate && 
                      ` (${exp.startDate.substring(0, 7)} - ${exp.endDate === 'Present' ? 'Present' : exp.endDate.substring(0, 7)})`
                    }
                  </Typography>
                  <Typography variant="body2">
                    {exp.description || ''}
                  </Typography>
                </ListItem>
              ))}
            </List>
          ) : (
            <Typography variant="body2">No work experience data available.</Typography>
          )}
          
          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            Skills
          </Typography>
          <Divider sx={{ mb: 2 }} />
          
          {profileData.skills && profileData.skills.length > 0 ? (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {profileData.skills.map((skill, index) => (
                <Chip
                  key={index}
                  label={`${skill.name} ${skill.endorsements ? `(${skill.endorsements})` : ''}`}
                  color="primary"
                  variant="outlined"
                  sx={{ m: 0.5 }}
                />
              ))}
            </Box>
          ) : (
            <Typography variant="body2">No skills data available.</Typography>
          )}
          
          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            Education
          </Typography>
          <Divider sx={{ mb: 2 }} />
          
          {profileData.education && profileData.education.length > 0 ? (
            <List>
              {profileData.education.map((edu, index) => (
                <ListItem key={index} sx={{ display: 'block', mb: 2 }}>
                  <Typography variant="subtitle2" color="primary.main">
                    {edu.school || 'Institution'}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {edu.degree || ''} {edu.fieldOfStudy || ''}
                    {edu.startDate && edu.endDate && 
                      ` (${edu.startDate.substring(0, 7)} - ${edu.endDate.substring(0, 7)})`
                    }
                  </Typography>
                  <Typography variant="body2">
                    {edu.description || ''}
                  </Typography>
                </ListItem>
              ))}
            </List>
          ) : (
            <Typography variant="body2">No education data available.</Typography>
          )}
          
          {/* Certifications Section */}
          {profileData.certifications && profileData.certifications.length > 0 && (
            <>
              <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                Certifications
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <List>
                {profileData.certifications.map((cert, index) => (
                  <ListItem key={index} sx={{ display: 'block', mb: 2 }}>
                    <Typography variant="subtitle2" color="primary.main">
                      {cert.name || `Certification ${index + 1}`}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                      Issued by: {cert.issuer || 'Unknown'}
                      {cert.date && ` (${cert.date})`}
                    </Typography>
                  </ListItem>
                ))}
              </List>
            </>
          )}
          
          {/* Projects Section */}
          {profileData.projects && profileData.projects.length > 0 && (
            <>
              <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                Key Projects
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <List>
                {profileData.projects.map((project, index) => (
                  <ListItem key={index} sx={{ display: 'block', mb: 2 }}>
                    <Typography variant="subtitle2" color="primary.main">
                      {project.name || `Project ${index + 1}`}
                    </Typography>
                    <Typography variant="body2">
                      {project.description || ''}
                    </Typography>
                    {project.technologies && project.technologies.length > 0 && (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                        {project.technologies.map((tech, techIndex) => (
                          <Chip 
                            key={techIndex} 
                            label={tech} 
                            size="small" 
                            variant="outlined" 
                            sx={{ 
                              bgcolor: 'rgba(9, 211, 172, 0.1)', 
                              borderColor: 'primary.main',
                              color: 'primary.main'
                            }} 
                          />
                        ))}
                      </Box>
                    )}
                  </ListItem>
                ))}
              </List>
            </>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <Box
      sx={{
        width: '100%',
        minHeight: '90vh',
        py: 3,
        background: 'linear-gradient(135deg, #0F172A 0%, #25314D 100%)'
      }}
    >
      <Container maxWidth="xl">
        <Typography variant="h3" sx={{ color: 'white', fontWeight: 'bold', mb: 3 }}>
          Career Transition Insights
        </Typography>
        
        <Paper sx={{ mb: 3, bgcolor: 'background.paper', borderRadius: 2, overflow: 'hidden', boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)' }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            textColor="primary"
            indicatorColor="primary"
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab label="Basic Network" />
            <Tab label="Enhanced Network" />
            <Tab label="Profile Details" />
          </Tabs>
          
          <Box sx={{ p: { xs: 1, sm: 2 } }}>
            {/* Basic Graph Visualization */}
            {activeTab === 0 && (
              <>
                <Typography variant="subtitle1" sx={{ mb: 2, mt: 1 }}>
                  Career Transition: Basic Network
                </Typography>
                {graphData.nodes.length > 0 ? (
                  <GraphVisualization data={graphData} />
                ) : (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    No data available for visualization. Please upload a profile.
                  </Alert>
                )}
              </>
            )}
            
            {/* Enhanced Graph Visualization */}
            {activeTab === 1 && (
              <>
                <Typography variant="subtitle1" sx={{ mb: 2, mt: 1 }}>
                  Career Transition: Enhanced Network with Skills & Education
                </Typography>
                {enhancedGraphData.nodes.length > 0 ? (
                  <AdvancedGraphVisualization data={enhancedGraphData} />
                ) : (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    No data available for visualization. Please upload a profile.
                  </Alert>
                )}
              </>
            )}
            
            {/* Profile Details */}
            {activeTab === 2 && (
              <>
                <Typography variant="subtitle1" sx={{ mb: 2, mt: 1 }}>
                  Profile Details
                </Typography>
                {renderProfileDetails()}
              </>
            )}
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};

export default ResultsPage; 